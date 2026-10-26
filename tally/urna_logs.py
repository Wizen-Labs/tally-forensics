"""Per-section ballot-box logs (logd.dat) from TSE's results site, for both 2026 rounds.

TSE publishes, for every section, a folder with the box's files (`bu.dat`, `rdv.dat`, `vota.vsc` and the event log
`-log.jez`, a zip holding `logd.dat`). The log of a round-2 box also holds its round-1 events, so one download serves
both rounds. Path: `arquivo-urna/<pleito>/dados/<uf>/<mun>/<zone>/<section>/<hash>/<file>`; the hash comes from the
section's `-aux.json`.

Data control (CLAUDE.md rule 4), adapted to about 500,000 logs of about 250 KB each:
- every log's SHA-256, size and Last-Modified go into the per-UF summary, so any log can be fetched again and
  checked;
- the raw log is kept only for sections that matter for the round-2 tests (closed at or after 17:30 local time on
  25/10, or anything unusual) and for a fixed 1% sample chosen by hash;
- the summary keeps no personal data: the log names poll workers by voter number, and those lines are only counted.
"""

import hashlib
import io
import json
import threading
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from . import DATA_DIR
from .live import BASE, CYCLE, UA

PLEITO_R2 = "3221"
DAYS = {"r1": "04/10/2026", "r2": "25/10/2026"}
LATE_FROM = "16:30:00"            # vote times kept from this local time on (they are only a few per box)
KEEP_CLOSE_FROM = "17:30:00"      # raw log kept if the round-2 close is at or after this local time

READY = "Urna pronta para receber votos"
CLOSE = "Procedimento de encerramento confirmado"
VOTE = "O voto do eleitor foi computado"
BIOMETRIC = "Tipo de habilita"       # "Tipo de habilitação do eleitor [biométrica]"
MANUAL = "habilitou o eleitor"       # "Mesário <voter number> habilitou o eleitor": counted, never stored


def parse_log(jez: bytes) -> dict:
    """Summary of one log, per round: first ready, last close, votes, vote times from LATE_FROM, a few counts."""
    with zipfile.ZipFile(io.BytesIO(jez)) as z:
        name = next(n for n in z.namelist() if n.endswith(".dat"))
        text = z.read(name).decode("latin1")
    out = {}
    for tag, day in DAYS.items():
        r = {"ready": None, "close": None, "n_ready": 0, "n_close": 0, "votes": 0, "first_vote": None,
             "last_vote": None, "late_votes": [], "biometric": 0, "manual": 0, "urn_ids": set()}
        for line in text.splitlines():
            if not line.startswith(day):
                continue
            f = line.split("\t")
            if len(f) < 5:
                continue
            t, msg = f[0][11:19], f[4]
            r["urn_ids"].add(f[2])
            if msg.startswith(READY):
                r["n_ready"] += 1
                r["ready"] = r["ready"] or t
            elif msg.startswith(CLOSE):
                r["n_close"] += 1
                r["close"] = t
            elif msg.startswith(VOTE):
                r["votes"] += 1
                r["first_vote"] = r["first_vote"] or t
                r["last_vote"] = t
                if t >= LATE_FROM:
                    r["late_votes"].append(t)
            elif msg.startswith(BIOMETRIC) and "biom" in msg:
                r["biometric"] += 1
            elif MANUAL in msg:
                r["manual"] += 1
        r["urn_ids"] = sorted(r["urn_ids"])
        out[tag] = r
    return out


def keep_raw(summary: dict, sha: str) -> bool:
    r2 = summary["r2"]
    unusual = r2["n_ready"] != 1 or r2["n_close"] != 1 or len(r2["urn_ids"]) != 1
    late = (r2["close"] or "") >= KEEP_CLOSE_FROM
    return unusual or late or int(sha[:4], 16) % 100 == 0


class LogCrawler:
    """Polite: at most `max_rps` requests per second across threads; on HTTP 429 every thread pauses (Retry-After,
    else 30 s, at most 120 s). Resumable: sections already in the UF's summary file are skipped."""

    def __init__(self, out: Path | None = None, pleito: str = PLEITO_R2, workers: int = 16, max_rps: float = 20.0,
                 log=print):
        self.out = out or DATA_DIR / "urna_logs" / f"p{pleito}"
        (self.out / "raw").mkdir(parents=True, exist_ok=True)
        self.pleito, self.workers, self.max_rps, self.log = pleito, workers, max_rps, log
        self._lock, self._rate_lock = threading.Lock(), threading.Lock()
        self._next, self.pause_until = 0.0, 0.0
        self.root = f"{BASE}/{CYCLE}/arquivo-urna/{pleito}"

    def _throttle(self) -> None:
        with self._rate_lock:
            start = max(time.time(), self._next, self.pause_until)
            self._next = start + 1.0 / self.max_rps
        wait = start - time.time()
        if wait > 0:
            time.sleep(wait)

    def _get(self, url: str, tries: int = 4) -> tuple[int, bytes | None, str | None]:
        for i in range(tries):
            self._throttle()
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                    return r.status, r.read(), r.headers.get("Last-Modified")
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    ra = (e.headers or {}).get("Retry-After", "")
                    with self._rate_lock:
                        self.pause_until = max(self.pause_until,
                                               time.time() + (min(int(ra), 120) if str(ra).isdigit() else 30))
                    continue
                if e.code == 404:
                    return 404, None, None
            except Exception:
                pass
            time.sleep(2 ** i)
        return 0, None, None

    def sections(self, uf: str) -> list[tuple[str, str, str]]:
        p = self.pleito.zfill(6)
        status, body, _ = self._get(f"{self.root}/config/{uf}/{uf}-p{p}-cs.json")
        if status != 200:
            raise RuntimeError(f"{uf}: section list unavailable (HTTP {status})")
        (self.out / f"cs_{uf}.json").write_bytes(body)
        j = json.loads(body.decode("utf-8-sig"))
        return [(mu["cd"], z["cd"], s["ns"]) for ab in j.get("abr", []) for mu in ab.get("mu", [])
                for z in mu.get("zon", []) for s in z.get("sec", [])]

    def _section(self, uf: str, mun: str, zone: str, sec: str) -> dict:
        p = self.pleito.zfill(6)
        folder = f"{self.root}/dados/{uf}/{mun}/{zone}/{sec}"
        row = {"uf": uf.upper(), "mun": mun, "zone": zone, "section": sec,
               "t_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "logs": []}
        status, body, _ = self._get(f"{folder}/p{p}-{uf}-m{mun}-z{zone}-s{sec}-aux.json")
        if status != 200:
            return {**row, "error": f"aux HTTP {status}"}
        aux = json.loads(body.decode("utf-8-sig"))
        row["aux_status"] = aux.get("st")
        for h in aux.get("hashes", []):
            name = next((a["nm"] for a in h.get("arq", []) if a.get("tp") == "log"), None)
            entry = {"hash": h.get("hash"), "status": h.get("st"), "received": f"{h.get('dr')} {h.get('hr')}"}
            if name is None:
                row["logs"].append({**entry, "error": "no log listed"})
                continue
            status, jez, lastmod = self._get(f"{folder}/{h['hash']}/{name}")
            if status != 200:
                row["logs"].append({**entry, "error": f"log HTTP {status}"})
                continue
            sha = hashlib.sha256(jez).hexdigest()
            try:
                summary = parse_log(jez)
            except Exception as e:
                summary, keep = None, True
                entry["error"] = f"parse: {type(e).__name__}: {e}"[:200]
            else:
                keep = keep_raw(summary, sha)
            if keep:
                raw = self.out / "raw" / uf / f"{name}.{sha[:12]}"
                raw.parent.mkdir(parents=True, exist_ok=True)
                if not raw.exists():
                    raw.write_bytes(jez)
            row["logs"].append({**entry, "file": name, "sha256": sha, "bytes": len(jez), "last_modified": lastmod,
                                "raw_kept": keep, "summary": summary})
        return row

    def run_uf(self, uf: str) -> dict:
        uf = uf.lower()
        path = self.out / f"sections_{uf}.jsonl"
        done = set()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "error" not in d and all("error" not in g for g in d["logs"]):
                    done.add((d["mun"], d["zone"], d["section"]))
        todo = [s for s in self.sections(uf) if s not in done]
        self.log(f"{uf}: {len(done):,} done, {len(todo):,} to fetch")
        t0, n, bad = time.time(), 0, 0
        with ThreadPoolExecutor(self.workers) as ex, open(path, "a", encoding="utf-8") as fh:
            for row in ex.map(lambda s: self._section(uf, *s), todo):
                failed = "error" in row or any("error" in g for g in row["logs"])
                bad += failed
                with self._lock:
                    fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                n += 1
                if n % 2000 == 0:
                    fh.flush()
                    self.log(f"{uf}: {n:,}/{len(todo):,} ({bad} with errors, {n / (time.time() - t0):.1f} sections/s)")
        self.log(f"{uf}: finished {n:,} sections in {time.time() - t0:,.0f} s, {bad} with errors")
        return {"uf": uf, "fetched": n, "errors": bad}
