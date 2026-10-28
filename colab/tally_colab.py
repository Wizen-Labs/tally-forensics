"""Independent live run-off collector and projector for Google Colab (backup / second opinion).

Deliberately independent from the main `tally` package:
- the round-1 BASE comes from TSE's municipal result files (resultados.tse.jus.br), not from ballot-box files;
- the MODEL is a plain municipal swing with two-level shrinkage, written from scratch;
- everything (raw responses, log, projections) is stored on Google Drive.
Only the Python standard library and pandas are used.
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

BASE_URL = "https://resultados.tse.jus.br/oficial"
CYCLE = "ele2026"
UFS = ["ac", "al", "am", "ap", "ba", "ce", "df", "es", "go", "ma", "mg", "ms", "mt", "pa", "pb", "pe", "pi", "pr",
       "rj", "rn", "ro", "rr", "rs", "sc", "se", "sp", "to", "zz"]
BRT = timezone(timedelta(hours=-3))
UA = {"User-Agent": "tally-forensics-colab/1.0 (research)"}


def n(x) -> int:
    try:
        return int(str(x).replace(".", "").replace(",", ""))
    except (TypeError, ValueError):
        return 0


class Fetcher:
    """Conditional GETs; every new body is stored once (sha256, gzip) and every request is logged.

    Polite to TSE's servers (they answered HTTP 429 "Too Many Requests" to bursts in testing, FINDINGS P9):
    at most `max_rps` requests per second across all threads, and on a 429 every thread pauses for the
    Retry-After time (30 s if absent, at most 120 s)."""

    def __init__(self, store: Path, workers: int = 16, max_rps: float = 15.0):
        self.store = Path(store)
        (self.store / "blobs").mkdir(parents=True, exist_ok=True)
        self.log_path = self.store / "fetch_log.jsonl"
        self.validators, self.bodies, self.workers = {}, {}, workers
        self.max_rps, self._next, self.pause_until = max_rps, 0.0, 0.0
        self._lock, self._rate_lock = threading.Lock(), threading.Lock()

    def _throttle(self) -> None:
        with self._rate_lock:
            start = max(time.time(), self._next, self.pause_until)
            self._next = start + 1.0 / self.max_rps
        wait = start - time.time()
        if wait > 0:
            time.sleep(wait)

    def get(self, url: str):
        self._throttle()
        h = dict(UA)
        et, lm = self.validators.get(url, (None, None))
        if et:
            h["If-None-Match"] = et
        if lm:
            h["If-Modified-Since"] = lm
        entry = {"t_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"), "url": url}
        t0 = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30) as r:
                body = r.read()
                self.validators[url] = (r.headers.get("ETag"), r.headers.get("Last-Modified"))
                entry["status"] = r.status
        except urllib.error.HTTPError as e:
            entry["status"] = e.code
            body = None
            if e.code == 429:                         # TSE asks us to slow down: pause every thread
                ra = (e.headers or {}).get("Retry-After", "")
                secs = min(int(ra), 120) if str(ra).isdigit() else 30
                with self._rate_lock:
                    self.pause_until = max(self.pause_until, time.time() + secs)
        except Exception as e:  # network errors must not stop the loop
            entry.update(status=0, error=str(e)[:200])
            body = None
        entry["ms"] = int(1000 * (time.time() - t0))
        if body is not None:
            sha = hashlib.sha256(body).hexdigest()
            blob = self.store / "blobs" / f"{sha}.json.gz"
            parsed = json.loads(body.decode("utf-8-sig"))
            with self._lock:
                if not blob.exists():
                    blob.write_bytes(gzip.compress(body))
                entry["sha256"] = sha
                self.bodies[url] = parsed
        with self._lock, open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        return entry["status"], self.bodies.get(url)

    def many(self, urls):
        with ThreadPoolExecutor(self.workers) as ex:
            return dict(zip(urls, ex.map(self.get, urls)))


def url_u(election: str, uf: str, mun: str | None = None) -> str:
    e6 = str(election).zfill(6)
    area = f"{uf}{str(mun).zfill(5)}" if mun else uf
    return f"{BASE_URL}/{CYCLE}/{election}/dados/{uf}/{area}-c0001-e{e6}-u.json"


def url_ab(election: str, uf: str) -> str:
    return f"{BASE_URL}/{CYCLE}/{election}/dados/{uf}/{uf}-e{str(election).zfill(6)}-ab.json"


def parse_u(j: dict) -> dict:
    votes = {}
    for carg in j.get("carg", []):
        if carg.get("cd") == "1":
            for agr in carg.get("agr", []):
                for par in agr.get("par", []):
                    for c in par.get("cand", []):
                        votes[str(c["n"])] = n(c.get("vap"))
    v, e, s = j.get("v", {}), j.get("e", {}), j.get("s", {})
    return {"votes": votes, "valid": n(v.get("vv")), "turnout": n(e.get("c")), "electorate": n(e.get("te")),
            "electorate_counted": n(e.get("est")),
            "sections_total": n(s.get("ts")), "sections_counted": n(s.get("st"))}


def parse_ab(j: dict, uf: str) -> list[dict]:
    rows = []
    for a in j.get("abr", []):
        if a.get("tpabr") == "mun":
            s, e = a.get("s", {}), a.get("e", {})
            rows.append({"uf": uf, "mun": str(int(a["cdabr"])), "ts": n(s.get("ts")), "st": n(s.get("st")),
                         "te": n(e.get("te")), "est": n(e.get("est")), "updated": f"{a.get('dt', '')} {a.get('ht', '')}"})
    return rows


# --------------------------------------------------------------------------------------------- base (round 1)

def build_base(fetcher: Fetcher, base_election: str, nr_a: str, nr_b: str, cache: Path) -> pd.DataFrame:
    """Round-1 result per municipality from TSE's municipal result files (one-off, about 5,800 requests)."""
    cache = Path(cache)
    if cache.exists():
        return pd.read_csv(cache, dtype={"uf": str, "mun": str})
    muns = []
    for uf, (_, j) in fetcher.many([url_ab(base_election, u) for u in UFS]).items():
        u = uf.split("/")[-2]
        if j:
            muns += [(u, r["mun"]) for r in parse_ab(j, u)]
    res = fetcher.many([url_u(base_election, u, m) for u, m in muns])
    rows = []
    for (u, m), (_, j) in zip(muns, res.values()):
        if j:
            p = parse_u(j)
            rows.append({"uf": u, "mun": m, "A1": p["votes"].get(nr_a, 0), "B1": p["votes"].get(nr_b, 0),
                         "valid1": p["valid"], "turnout1": p["turnout"], "electorate1": p["electorate"]})
    base = pd.DataFrame(rows)
    base.to_csv(cache, index=False)
    return base


# --------------------------------------------------------------------------------------------- live state

class Live:
    """Live state. Each municipality's votes are stored TOGETHER with the progress figures of the same municipal
    file (sections and electorate counted), so a failed download can never pair new progress with old or missing
    votes: the municipality simply keeps its last consistent snapshot and is retried next cycle."""

    def __init__(self, fetcher: Fetcher, election: str, nr_a: str, nr_b: str, max_mun_per_cycle: int = 900):
        self.f, self.e, self.a, self.b = fetcher, str(election), nr_a, nr_b
        self.progress, self.mun_votes, self.national, self.retry = {}, {}, None, set()
        self.status_counts, self.max_mun = {}, max_mun_per_cycle

    def cycle(self) -> dict:
        t0 = time.time()
        fixed = [url_u(self.e, "br")] + [url_ab(self.e, u) for u in UFS]
        res = self.f.many(fixed)
        fixed_failed = sum(1 for u in fixed if res[u][0] not in (200, 304))
        self.national = parse_u(res[url_u(self.e, "br")][1]) if res[url_u(self.e, "br")][1] else self.national
        changed = []
        for u in UFS:
            j = res[url_ab(self.e, u)][1]
            for r in parse_ab(j, u) if j else []:
                key = (u, r["mun"])
                old = self.progress.get(key)
                self.progress[key] = r
                if r["st"] > 0 and (old is None or (old["st"], old["updated"]) != (r["st"], r["updated"])
                                    or key not in self.mun_votes):
                    changed.append(key)
        # retries first, then the largest electorates; anything beyond the per-cycle cap waits for the next cycle
        # (it keeps its last consistent snapshot meanwhile)
        pending = list(dict.fromkeys(sorted(self.retry) + sorted(
            changed, key=lambda k: -self.progress.get(k, {}).get("te", 0))))
        changed, deferred = pending[:self.max_mun], pending[self.max_mun:]
        mres = self.f.many([url_u(self.e, u, m) for u, m in changed])
        failed, self.retry = 0, set()
        statuses = [res[u][0] for u in fixed]
        for key, (status, j) in zip(changed, mres.values()):
            statuses.append(status)
            if j:
                p = parse_u(j)
                self.mun_votes[key] = {"A2c": p["votes"].get(self.a, 0), "B2c": p["votes"].get(self.b, 0),
                                       "st": p["sections_counted"], "ts": p["sections_total"],
                                       "est": p["electorate_counted"], "te": p["electorate"]}
            else:
                failed += 1
                self.retry.add(key)                 # keep the last consistent snapshot; retry next cycle
        self.retry.update(deferred)
        for s in statuses:
            self.status_counts[s] = self.status_counts.get(s, 0) + 1
        requests = len(fixed) + len(changed)
        return {"t_brt": datetime.now(BRT).strftime("%H:%M:%S"), "municipal_fetched": len(changed),
                "municipal_deferred": len(deferred),
                "municipal_failed": failed, "fixed_failed": fixed_failed, "requests": requests,
                "failure_rate": round((failed + fixed_failed) / max(requests, 1), 3),
                "statuses": {str(k): statuses.count(k) for k in sorted(set(statuses), key=str)},
                "seconds": round(time.time() - t0, 1)}

    def table(self) -> pd.DataFrame:
        """One row per municipality. Progress (st, ts, est, te) comes from the same municipal file as the votes;
        a municipality whose file has never been read counts as not yet counted."""
        rows = []
        for (u, m), r in self.progress.items():
            mv = self.mun_votes.get((u, m))
            if mv:
                rows.append({"uf": u, "mun": m, "updated": r["updated"], **mv})
            else:
                rows.append({"uf": u, "mun": m, "updated": r["updated"], "A2c": 0, "B2c": 0,
                             "st": 0, "ts": r["ts"], "est": 0, "te": r["te"]})
        return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------- model

def project(live: pd.DataFrame, base: pd.DataFrame, k_mun: float = 2000.0, k_uf: float = 10000.0) -> dict:
    """Municipal swing on the two-party share, shrunk municipality -> UF -> Brazil. Abroad (ZZ) is modelled as one
    more UF: left out, its uncounted votes would count as zero (FINDINGS P10). Only municipalities missing from the
    base are taken as counted, without projection."""
    d = live.merge(base, on=["uf", "mun"], how="left")
    home = d[d["A1"].notna()].copy()
    home["frac"] = (home["est"] / home["te"].clip(lower=1)).where(home["st"] < home["ts"], 1.0)
    home.loc[home["st"] == 0, "frac"] = 0.0
    v1 = (home["A1"] + home["B1"]).clip(lower=1)
    s1 = home["A1"] / v1
    v1c = v1 * home["frac"]
    v2c = home["A2c"] + home["B2c"]
    home["sw_num"] = home["A2c"] - v2c * s1                  # votes above the round-1 share
    home["v2c"], home["v1c"] = v2c, v1c
    tot = home[["sw_num", "v2c", "v1c"]].sum()
    sw_br = tot["sw_num"] / max(tot["v2c"], 1)
    tr_br = tot["v2c"] / max(tot["v1c"], 1)
    g = home.groupby("uf")[["sw_num", "v2c", "v1c"]].sum()
    sw_uf = (g["sw_num"] + k_uf * sw_br) / (g["v2c"] + k_uf)
    tr_uf = (g["v2c"] + k_uf * tr_br) / (g["v1c"] + k_uf)
    sw = (home["sw_num"] + k_mun * home["uf"].map(sw_uf)) / (home["v2c"] + k_mun)
    tr = (home["v2c"] + k_mun * home["uf"].map(tr_uf)) / (home["v1c"] + k_mun)
    v_rem = v1 * (1 - home["frac"]) * tr
    a_rem = (s1 + sw).clip(0, 1) * v_rem
    zz = d[d["A1"].isna()]                                  # not in the base: counted votes only
    A = home["A2c"].sum() + a_rem.sum() + zz["A2c"].sum()
    B = home["B2c"].sum() + (v_rem - a_rem).sum() + zz["B2c"].sum()
    counted_e = (home["frac"] * home["te"]).sum()
    # coverage gate counts the 27 UFs only: abroad is modelled but is not a state
    uf_cov = home[home["uf"] != "zz"].groupby("uf").apply(lambda x: (x["frac"] * x["te"]).sum() / max(x["te"].sum(), 1),
                                      include_groups=False)
    return {"share_a": 100 * A / (A + B), "pct_electorate_counted": 100 * counted_e / max(home["te"].sum(), 1),
            "ufs_with_1pct": int((uf_cov >= 0.01).sum()), "swing_br_pp": 100 * sw_br}


def ready(p: dict, min_pct: float = 2.0, min_ufs: int = 24) -> bool:
    """Publication gate: enough counted AND geographically spread (owner's representativeness rule)."""
    return p["pct_electorate_counted"] >= min_pct and p["ufs_with_1pct"] >= min_ufs


def make_card(csv_path, out_png, name_a="Flávio Bolsonaro", name_b="Lula", half_width=0.8, simulation=False,
              author="Eduardo Wizentier", date_label="25 de outubro de 2026", watermark=None):
    """Media card (1080x1350 PNG): latest ready projection, call rule, and the projection over time."""
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib import font_manager  # noqa: F401  (default DejaVu Sans if nothing nicer is installed)

    d = pd.read_csv(csv_path)
    counting = d[d["pct_electorate_counted"] > 0]             # rows before the first result would pull the chart to 0%
    d = counting.reset_index(drop=True) if len(counting) else d
    d["ready"] = d["ready"].astype(str).str.lower().isin(["true", "1"])
    ready = d[d["ready"]]
    last = (ready if len(ready) else d).iloc[-1]
    a = float(last["projection_a"]) if len(ready) else float("nan")
    b = 100 - a
    lo, hi = a - half_width, a + half_width
    if not len(ready):
        status, status_col = "Aguardando cobertura geográfica suficiente", "#6b6f76"
    elif lo > 50:
        status, status_col = f"Vencedor projetado: {name_a}", "#1f6f8b"
    elif hi < 50:
        status, status_col = f"Vencedor projetado: {name_b}", "#b5523a"
    else:
        status, status_col = "Empate técnico: ainda sem vencedor projetado", "#8a6d1d"
    mark = watermark or ("SIMULAÇÃO" if simulation else None)
    if mark:
        status = f"{mark} · " + status

    INK, MUTED, GRID, BG = "#15171a", "#6b6f76", "#e4e6ea", "#fbfbfc"
    CA, CB = "#1f6f8b", "#b5523a"            # neutral, non-party colours
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100, facecolor=BG)

    def txt(x, y, s, **k):
        fig.text(x, y, s, color=k.pop("color", INK), family=k.pop("family", "DejaVu Sans"), **k)

    txt(0.07, 0.945, "PROJEÇÃO DO 2º TURNO PRESIDENCIAL", size=15, weight="bold", color=MUTED)
    txt(0.07, 0.918, f"{date_label}  ·  atualizado às {str(last['t_brt'])[:5].replace(':', 'h')}", size=15, color=MUTED)
    txt(0.07, 0.885, f"{float(last['pct_electorate_counted']):.1f}".replace(".", ",") + "% do eleitorado apurado  ·  "
                     f"{int(last['ufs_with_1pct'])} de 27 estados com dados", size=15, color=MUTED)

    if len(ready):
        txt(0.07, 0.80, name_a, size=24, color=CA, weight="bold")
        txt(0.93, 0.80, name_b, size=24, color=CB, weight="bold", ha="right")
        txt(0.07, 0.715, f"{a:.1f}%".replace(".", ","), size=78, color=CA, weight="bold")
        txt(0.93, 0.715, f"{b:.1f}%".replace(".", ","), size=78, color=CB, weight="bold", ha="right")
        bar = fig.add_axes([0.07, 0.675, 0.86, 0.022])
        bar.barh([0], [a], color=CA, height=1)
        bar.barh([0], [b], left=[a], color=CB, height=1)
        bar.axvline(50, color=BG, lw=3)
        bar.set_xlim(0, 100); bar.axis("off")
        txt(0.5, 0.645, f"margem estimada ±{half_width:.1f}".replace(".", ",") + " ponto percentual", size=14, color=MUTED, ha="center")
    else:
        txt(0.07, 0.74, "Projeção ainda não publicada", size=36, weight="bold")
        txt(0.07, 0.70, "Esperando apuração espalhada por todo o país", size=18, color=MUTED)

    fig.text(0.5, 0.597, status, ha="center", va="center", size=18, weight="bold", color=status_col,
             bbox=dict(boxstyle="round,pad=0.7,rounding_size=0.9", fc=matplotlib.colors.to_rgba(status_col, 0.10),
                       ec="none"))

    ax = fig.add_axes([0.11, 0.17, 0.82, 0.36], facecolor=BG)
    t = pd.to_datetime("2000-01-01 " + d["t_brt"].astype(str))
    if len(ready):
        tr = t[d["ready"]]
        pa = ready["projection_a"].astype(float)
        ax.fill_between(tr, pa - half_width, pa + half_width, color=CA, alpha=0.12, lw=0)
        ax.plot(tr, pa, color=CA, lw=3, solid_capstyle="round", label=f"projeção ({name_a})")
    ax.plot(t, d["raw_a"].astype(float), color=MUTED, lw=1.5, ls=(0, (3, 3)), label="placar parcial bruto")
    ax.axhline(50, color=INK, lw=1, alpha=0.4)
    ax.set_ylabel(f"% de {name_a} entre os dois", color=MUTED, size=13)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.2f}".replace(".", ",").rstrip("0").rstrip(",")))
    if t.nunique() < 2:                      # one point only: give the time axis a sensible span
        ax.set_xlim(t.min() - pd.Timedelta(minutes=10), t.max() + pd.Timedelta(minutes=10))
        ax.plot(t, d["projection_a"].astype(float), "o", color=CA, ms=9)
    ax.xaxis.set_major_locator(matplotlib.dates.AutoDateLocator(minticks=3, maxticks=8))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Hh%M"))
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.tick_params(colors=MUTED, labelsize=12)
    ax.legend(frameon=False, fontsize=12, labelcolor=MUTED, loc="upper right")
    txt(0.07, 0.555, "Evolução ao longo da apuração", size=16, weight="bold")

    txt(0.07, 0.095, "Projeção estatística independente, NÃO é resultado oficial. Fonte dos dados: TSE.",
        size=13, weight="bold")
    txt(0.07, 0.07, "Modelo: comparação de cada município com o próprio 1º turno, a partir das urnas já apuradas.",
        size=12, color=MUTED)
    txt(0.07, 0.035, f"{author}  ·  desenvolvido com Claude Opus 5.5 (Anthropic)", size=12, color=MUTED)
    if mark:
        fig.text(0.5, 0.42, mark, size=110 if len(mark) <= 10 else 50, color="#d0342c", alpha=0.13, ha="center", va="center",
                 rotation=28, weight="bold")
    fig.savefig(out_png, dpi=100, facecolor=BG)
    plt.close(fig)
    return out_png


def access_test(election: str = "6257") -> pd.DataFrame:
    """Can this machine reach TSE's results site, and how fast?"""
    urls = [f"{BASE_URL}/comum/config/ele-c.json", url_u(election, "br"), url_ab(election, "sp"),
            url_u(election, "sp", "71072")]
    rows = []
    for u in urls:
        t0 = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
                body = r.read()
                rows.append({"file": u.rsplit("/", 1)[-1], "status": r.status, "kB": round(len(body) / 1024, 1),
                             "ms": int(1000 * (time.time() - t0)), "last_modified": r.headers.get("Last-Modified")})
        except Exception as e:
            rows.append({"file": u.rsplit("/", 1)[-1], "status": "ERROR", "kB": None,
                         "ms": int(1000 * (time.time() - t0)), "last_modified": str(e)[:80]})
    return pd.DataFrame(rows)
