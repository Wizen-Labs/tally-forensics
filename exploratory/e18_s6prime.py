"""E18: deviation 01 (commitments/deviation_01_s6prime.md), S6' on both halves and rounds. Run once.

Writes `reports/h8r2/s6prime/`: `<half>_r<round>_<stat>.csv` (every tested bin), `flagged.csv` (every flagged bin;
for A with the peaking boxes and their sections) and `result.json` (counts and coincidences).

    .venv/Scripts/python exploratory/e18_s6prime.py          (--dry: code check on RR round 1, writes nothing)
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tally import s6prime as s6
from e15_s1_s6 import TRAILS, box_table

OUT = Path(__file__).resolve().parents[1] / "reports" / "h8r2" / "s6prime"


def main() -> None:
    dry = sys.argv[1:2] == ["--dry"]                 # code check on round 1 of RR (half D) only; writes nothing
    b, _ = box_table()
    b = b[b["uf"] != "zz"]
    if dry:
        b = b[b["uf"] == "rr"]
    else:
        OUT.mkdir(parents=True, exist_ok=True)
    off = b.set_index("box")["tz_offset_h"]
    sec = b.set_index("box")[["uf", "mun", "zone", "sec"]]
    flagged, res = [], {}
    for half in (("D",) if dry else ("D", "C")):
        for rnd in ((1,) if dry else (1, 2)):
            keep = set(b.loc[(b["half"] == half) & ~b["excl_r1" if rnd == 1 else "excl_all"], "box"])
            parts = []
            for uf in sorted(b.loc[b["half"] == half, "uf"].unique()):
                v = pd.read_parquet(TRAILS / f"{uf}_r{rnd}.parquet", columns=["box", "t_computed"])
                parts.append(v[v["box"].isin(keep)])
            v = pd.concat(parts, ignore_index=True)
            d, e = s6.minutes(v, off)
            del v, parts
            r = {"A": s6.stat_a(d, e), "B1": s6.stat_b(d, e, 1), "B2": s6.stat_b(d, e, 2)}
            for stat, x in r.items():
                if not dry:
                    x.to_csv(OUT / f"{half}_r{rnd}_{stat}.csv", index=False)
                for _, row in x[x["flag"]].iterrows():
                    m = int(row["minute"])
                    rec = {"half": half, "rnd": rnd, "stat": stat, "minute": m,
                           "brt": f"{m // 60:02d}:{m % 60:02d}", "count": row["count"],
                           "expected": round(float(row["expected"]), 2), "p": float(row["p"])}
                    if stat == "A":
                        c = d[d["minute"] == m].groupby("box").size()
                        rec["boxes"] = ";".join(f"{u}/{mu}/{z}/{s}" for u, mu, z, s in
                                                sec.loc[c[c >= s6.PEAK].index].itertuples(index=False))
                    flagged.append(rec)
                res[f"{half}_r{rnd}_{stat}"] = {"tested": int(x["tested"].sum()), "flagged": int(x["flag"].sum()),
                                                "min_p": float(x["p"].min())}
            print(half, rnd, {k: v for k, v in res.items() if k.startswith(f"{half}_r{rnd}")}, flush=True)
    if dry:
        print(len(flagged), "flagged bins in the dry run")
        return
    fl = pd.DataFrame(flagged, columns=["half", "rnd", "stat", "minute", "brt", "count", "expected", "p", "boxes"])
    fl.to_csv(OUT / "flagged.csv", index=False)
    r2 = {h: sorted(fl.loc[(fl["half"] == h) & (fl["rnd"] == 2), "minute"].unique().tolist()) for h in ("D", "C")}
    ctrl = sorted(fl.loc[fl["rnd"] == 1, "minute"].unique().tolist())
    res["coincident_round2"] = s6.coincide(r2["D"], r2["C"], ctrl)
    res["decision"] = "unexplained pattern" if res["coincident_round2"] else "no signature found so far"
    (OUT / "result.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
