"""Live collector for TSE's results site (resultados.tse.jus.br), presidential race only.

Every cycle it fetches, with conditional requests (ETag / Last-Modified):
- the national and 27+1 UF result files (`-u.json`, office 1 = President);
- the 28 progress files (`-ab.json`): sections totalised per municipality;
- the 28 section-configuration files (`-cs.json`): to see whether section timestamps move during the count;
- the municipal result files (`<uf><mun>-c0001-...-u.json`) only for municipalities whose progress changed.

Data control (CLAUDE.md rule 4): every response body is stored once, content-addressed by SHA-256 and gzipped, and
every request is appended to `fetch_log.jsonl`. Nothing is ever overwritten, so any moment of the count can be
replayed later for analysis and forensics.
"""

import gzip
import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from . import DATA_DIR
from .config import ufs

BASE = "https://resultados.tse.jus.br/oficial"
CYCLE = "ele2026"
OFFICE = "0001"
BRT = timezone(timedelta(hours=-3))
UA = {"User-Agent": "tally-forensics/0.3 (research; github.com/Wizen-Labs/tally-forensics)"}


def _num(x) -> int:
    try:
        return int(str(x).replace(".", "").replace(",", ""))
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------------------------------------------------------- parsers

def parse_ab(j: dict, uf: str) -> pd.DataFrame:
    """Progress file -> one row per municipality."""
    rows = []
    for a in j.get("abr", []):
        if a.get("tpabr") != "mun":
            continue
        s, e = a.get("s", {}), a.get("e", {})
        rows.append({"SG_UF": uf.upper(), "CD_MUNICIPIO": str(int(a["cdabr"])),
                     "sections_total": _num(s.get("ts")), "sections_counted": _num(s.get("st")),
                     "electorate_total": _num(e.get("te")), "electorate_counted": _num(e.get("est")),
                     "updated": f"{a.get('dt', '')} {a.get('ht', '')}".strip()})
    return pd.DataFrame(rows)


def parse_u(j: dict) -> dict:
    """Result file (any level) -> votes per candidate number for the presidential race, plus totals."""
    out = {"generated": f"{j.get('dg', '')} {j.get('hg', '')}".strip(),
           "sections_total": _num(j.get("s", {}).get("ts")), "sections_counted": _num(j.get("s", {}).get("st")),
           "electorate_total": _num(j.get("e", {}).get("te")),
           "electorate_counted": _num(j.get("e", {}).get("est")),
           "blank": _num(j.get("v", {}).get("vb")), "null": _num(j.get("v", {}).get("tvn")),
           "valid": _num(j.get("v", {}).get("vv")), "votes": {}}
    for carg in j.get("carg", []):
        if carg.get("cd") != "1":
            continue
        for agr in carg.get("agr", []):
            for par in agr.get("par", []):
                for cand in par.get("cand", []):
                    out["votes"][str(cand["n"])] = _num(cand.get("vap"))
    return out


def parse_cs(j: dict, uf: str) -> pd.DataFrame:
    rows = []
    for ab in j.get("abr", []):
        for mu in ab.get("mu", []):
            for z in mu.get("zon", []):
                for s in z.get("sec", []):
                    rows.append((uf.upper(), str(int(mu["cd"])), str(int(z["cd"])), str(int(s["ns"])),
                                 f"{s.get('da', '')} {s.get('ha', '')}".strip()))
    return pd.DataFrame(rows, columns=["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "stamp"])


# ---------------------------------------------------------------------------------------------------------- collector

class Collector:
    """Polite to TSE's servers, which answered HTTP 429 to bursts in testing (FINDINGS P9): at most `max_rps`
    requests per second across all threads, a global pause on 429 (Retry-After, else 30 s, at most 120 s), and at
    most `max_mun_per_cycle` municipal files per cycle, largest electorates first (the rest wait one cycle)."""

    def __init__(self, election: str, archive: Path | None = None, workers: int = 16, uf_list=None, log=print,
                 max_rps: float = 15.0, max_mun_per_cycle: int = 900):
        self.election = str(election)
        self.e6 = self.election.zfill(6)
        self.archive = archive or DATA_DIR / "live" / f"{CYCLE}_e{self.e6}"
        self.blobs = self.archive / "blobs"
        self.blobs.mkdir(parents=True, exist_ok=True)
        self.log_path = self.archive / "fetch_log.jsonl"
        self.workers = workers
        self.ufs = [u.lower() for u in (uf_list or ufs())]
        self.log = log
        self._lock, self._rate_lock = threading.Lock(), threading.Lock()
        self.max_rps, self._next, self.pause_until = max_rps, 0.0, 0.0
        self.max_mun = max_mun_per_cycle
        self.validators: dict[str, tuple[str | None, str | None]] = {}
        self.latest: dict[str, str] = {}          # url -> sha256 of the latest body
        self.ab_state: dict[str, tuple] = {}      # municipality -> (counted, updated)
        self.state_path = self.archive / "collector_state.json"
        if self.state_path.exists():               # resume after a restart without re-downloading everything
            st = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.validators = {k: tuple(v) for k, v in st["validators"].items()}
            self.latest = st["latest"]
            self.ab_state = {k: tuple(v) for k, v in st["ab_state"].items()}
        self.pleito = self._resolve_pleito()

    def _save_state(self) -> None:
        tmp = self.state_path.with_suffix(".part")
        tmp.write_text(json.dumps({"validators": self.validators, "latest": self.latest,
                                   "ab_state": self.ab_state}), encoding="utf-8")
        tmp.replace(self.state_path)

    # URL builders
    def url_u(self, uf: str, mun: str | None = None) -> str:
        area = f"{uf}{str(mun).zfill(5)}" if mun else uf
        return f"{BASE}/{CYCLE}/{self.election}/dados/{uf}/{area}-c{OFFICE}-e{self.e6}-u.json"

    def url_ab(self, uf: str) -> str:
        return f"{BASE}/{CYCLE}/{self.election}/dados/{uf}/{uf}-e{self.e6}-ab.json"

    def url_cs(self, uf: str) -> str:
        p = self.pleito.zfill(6)
        return f"{BASE}/{CYCLE}/arquivo-urna/{self.pleito}/config/{uf}/{uf}-p{p}-cs.json"

    def _resolve_pleito(self) -> str:
        status, body = self._get(f"{BASE}/comum/config/ele-c.json", conditional=False)
        cfg = json.loads(body.decode("utf-8-sig"))
        for pl in cfg.get("pl", []):
            if any(e.get("cd") == self.election for e in pl.get("e", [])):
                return str(pl["cd"])
        raise ValueError(f"election {self.election} not found in ele-c.json")

    # HTTP with conditional requests, content-addressed storage and an append-only log
    def _throttle(self) -> None:
        with self._rate_lock:
            start = max(time.time(), self._next, self.pause_until)
            self._next = start + 1.0 / self.max_rps
        wait = start - time.time()
        if wait > 0:
            time.sleep(wait)

    def _get(self, url: str, conditional: bool = True) -> tuple[int, bytes | None]:
        self._throttle()
        headers = dict(UA)
        etag, lastmod = self.validators.get(url, (None, None)) if conditional else (None, None)
        if etag:
            headers["If-None-Match"] = etag
        if lastmod:
            headers["If-Modified-Since"] = lastmod
        t = datetime.now(timezone.utc)
        entry = {"t_utc": t.isoformat(timespec="milliseconds"), "url": url}
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
                body = r.read()
                status = r.status
                self.validators[url] = (r.headers.get("ETag"), r.headers.get("Last-Modified"))
                entry.update(status=status, last_modified=r.headers.get("Last-Modified"))
        except urllib.error.HTTPError as e:
            entry.update(status=e.code)
            if e.code == 429:                         # TSE asks us to slow down: pause every thread
                ra = (e.headers or {}).get("Retry-After", "")
                secs = min(int(ra), 120) if str(ra).isdigit() else 30
                with self._rate_lock:
                    self.pause_until = max(self.pause_until, time.time() + secs)
            self._append(entry)
            return e.code, None
        except Exception as e:  # timeouts, resets, truncated reads: never let one file break the cycle
            entry.update(status=0, error=f"{type(e).__name__}: {e}"[:200])
            self._append(entry)
            return 0, None
        sha = hashlib.sha256(body).hexdigest()
        blob = self.blobs / f"{sha}.json.gz"
        with self._lock:                        # parallel downloads may carry identical bodies
            if not blob.exists():
                tmp = blob.with_suffix(f".{threading.get_ident()}.part")
                tmp.write_bytes(gzip.compress(body))
                tmp.replace(blob)
            entry.update(sha256=sha, bytes=len(body), changed=self.latest.get(url) != sha)
            self.latest[url] = sha
        self._append(entry)
        return status, body

    def _append(self, entry: dict) -> None:
        with self._lock, open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")

    def _many(self, urls: list[str]) -> dict[str, tuple[int, bytes | None]]:
        with ThreadPoolExecutor(self.workers) as ex:
            return dict(zip(urls, ex.map(self._get, urls)))

    # one polling cycle
    def cycle(self, with_cs: bool = True) -> dict:
        t0 = time.time()
        fixed = [self.url_u("br")] + [self.url_u(u) for u in self.ufs] + [self.url_ab(u) for u in self.ufs]
        if with_cs:
            fixed += [self.url_cs(u) for u in self.ufs]
        res = self._many(fixed)
        changed_mun, electorate = [], {}
        for uf in self.ufs:
            status, body = res[self.url_ab(uf)]
            if body is None:
                continue
            ab = parse_ab(json.loads(body.decode("utf-8-sig")), uf)
            for r in ab.itertuples():
                key = f"{uf}:{r.CD_MUNICIPIO}"
                state = (r.sections_counted, r.updated)
                if r.sections_counted > 0 and self.ab_state.get(key) != state:
                    changed_mun.append((uf, r.CD_MUNICIPIO))
                    electorate[(uf, r.CD_MUNICIPIO)] = r.electorate_total
                self.ab_state[key] = state
        changed_mun.sort(key=lambda k: -electorate.get(k, 0))          # largest electorates first
        changed_mun, deferred = changed_mun[:self.max_mun], changed_mun[self.max_mun:]
        for uf, mun in deferred:                                        # not fetched now: retried next cycle
            self.ab_state.pop(f"{uf}:{mun}", None)
        mres = self._many([self.url_u(uf, mun) for uf, mun in changed_mun])
        for (uf, mun), (status, _) in zip(changed_mun, mres.values()):
            if status not in (200, 304):              # forget the state so the next cycle retries this file
                self.ab_state.pop(f"{uf}:{mun}", None)
        summary = {
            "t_brt": datetime.now(BRT).strftime("%H:%M:%S"),
            "fixed_requests": len(fixed),
            "fixed_downloaded": sum(1 for u in fixed if res[u][1] is not None),
            "fixed_not_modified": sum(1 for u in fixed if res[u][0] == 304),
            "fixed_errors": sum(1 for u in fixed if res[u][0] not in (200, 304)),
            "municipal_requests": len(mres),
            "municipal_deferred": len(deferred),
            "municipal_errors": sum(1 for v in mres.values() if v[0] not in (200, 304)),
            "seconds": round(time.time() - t0, 1),
        }
        self._save_state()
        self.log(f"[live] {summary}")
        return summary

    def run(self, interval: int = 60, until: str | None = None, with_cs: bool = True, on_cycle=None) -> None:
        stop = None
        if until:
            h, m = map(int, until.split(":"))
            stop = datetime.now(BRT).replace(hour=h, minute=m, second=0, microsecond=0)
        while True:
            started = time.time()
            try:
                self.cycle(with_cs)
                if on_cycle:
                    on_cycle()
            except Exception as e:  # a bad cycle must never stop the collector on election night
                self.log(f"[live] cycle error, continuing: {type(e).__name__}: {e}")
            if stop and datetime.now(BRT) >= stop:
                break
            time.sleep(max(1.0, interval - (time.time() - started)))


# ---------------------------------------------------------------------------------------------------------- replay

def load_state(archive: Path, as_of_utc: str | None = None) -> dict:
    """Rebuilds what was known at a moment (default: the latest) from the archive alone."""
    latest = {}
    with open(archive / "fetch_log.jsonl", encoding="utf-8") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except json.JSONDecodeError:      # a damaged line must not stop the replay; it is simply skipped
                continue
            if "sha256" not in e or (as_of_utc and e.get("t_utc", "") > as_of_utc):
                continue
            latest[e["url"]] = e["sha256"]

    def body(sha):
        return json.loads(gzip.decompress((archive / "blobs" / f"{sha}.json.gz").read_bytes()).decode("utf-8-sig"))

    ab, mun, uf_tot, br = [], [], {}, None
    for url, sha in latest.items():
        name = url.rsplit("/", 1)[-1]
        uf = url.rsplit("/", 2)[-2]
        if name.endswith("-ab.json"):
            ab.append(parse_ab(body(sha), uf))
        elif name.endswith("-u.json"):
            area = name.split("-c")[0]
            parsed = parse_u(body(sha))
            if area == "br":
                br = parsed
            elif area == uf:
                uf_tot[uf.upper()] = parsed
            else:
                mun.append({"SG_UF": uf.upper(), "CD_MUNICIPIO": str(int(area[len(uf):])),
                            **{f"v_{k}": v for k, v in parsed["votes"].items()},
                            "blank": parsed["blank"], "null": parsed["null"],
                            # progress as stated by the SAME file as the votes (consistent snapshot)
                            "u_sections_counted": parsed["sections_counted"],
                            "u_sections_total": parsed["sections_total"],
                            "u_electorate_counted": parsed["electorate_counted"],
                            "u_electorate_total": parsed["electorate_total"]})
    return {"ab": pd.concat(ab, ignore_index=True) if ab else pd.DataFrame(),
            "municipal": pd.DataFrame(mun).fillna(0), "uf": uf_tot, "br": br}
