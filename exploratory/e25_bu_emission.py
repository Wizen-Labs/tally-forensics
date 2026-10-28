"""E25: does any round-2 BU look generated long after its box closed (author's hypothesis: access to many boxes
between 17:00 and 19:00 BRT, while TSE registered almost no reception)?

Per box: the BU's own emission time (first timestamp in `bu.dat`, box clock) and urn id, against the log's close
time and urn ids (H7r2 crawl summary). Writes `reports/h8r2/sweep/bu_emission.csv`.
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "exploratory"))
from e23_c04_collapse_a1 import _tree, _nodes, BU, LOGS


def header(b: bytes) -> tuple[str | None, int | None]:
    """BU emission timestamp and the urn serial (the first integer of six or more digits after the header)."""
    t = _tree(b)
    ts = next((v.decode() for tag, v in _walk_leaves(t) if tag == 0x1B and len(v) == 15 and v[8:9] == b"T"), None)
    return ts, None


def _walk_leaves(tree):
    for tag, v in tree:
        if isinstance(v, list):
            yield from _walk_leaves(v)
        else:
            yield tag, v


def secs(hms: str) -> int:
    h, m, s = map(int, hms.split(":"))
    return h * 3600 + m * 60 + s


def main() -> None:
    rows = []
    for jl in sorted(LOGS.glob("sections_*.jsonl")):
        uf = jl.stem.split("_")[1]
        close = {}
        for line in jl.open(encoding="utf-8"):
            s = json.loads(line)
            for lg in s.get("logs", []):
                r2 = (lg.get("summary") or {}).get("r2") or {}
                close[lg.get("hash")] = (r2.get("close"), r2.get("last_vote"), lg.get("received"))
        for line in (BU / f"manifest_{uf}.jsonl").open(encoding="utf-8"):
            r = json.loads(line)
            ts, _ = header((BU / uf / f"{r['file']}.{r['sha256'][:12]}").read_bytes())
            c, last, rec = close.get(r["hash"], (None, None, None))
            rows.append({"uf": uf, "mun": int(r["mun"]), "zone": int(r["zone"]), "sec": int(r["section"]),
                         "bu_emitted": ts, "log_close": c, "log_last_vote": last, "tse_received": rec})
    d = pd.DataFrame(rows)
    em = d["bu_emitted"].str[9:15]
    d["emit_s"] = em.str[:2].astype(float) * 3600 + em.str[2:4].astype(float) * 60 + em.str[4:6].astype(float)
    d["close_s"] = d["log_close"].map(lambda x: secs(x) if isinstance(x, str) else None)
    d["emit_minus_close_min"] = (d["emit_s"] - d["close_s"]) / 60
    d.to_csv(ROOT / "reports" / "h8r2" / "sweep" / "bu_emission.csv", index=False)
    x = d["emit_minus_close_min"]
    print("boxes", len(d), "| with both times", int(x.notna().sum()))
    print(pd.cut(x, [-1e9, -1, 0, 2, 5, 10, 30, 60, 1e9]).value_counts().sort_index().to_string())
    print(d[x.abs() > 10].sort_values("emit_minus_close_min").to_string())


if __name__ == "__main__":
    main()
