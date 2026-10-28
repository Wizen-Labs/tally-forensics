"""E16: sealed test C-02 (commitments/c_test_02_s5_poll_worker_scores.md). Run once.

Reads, for the S5-tested boxes of half C only, the columns box, n_scores, score_last and bio of the E12 trail tables,
and evaluates P1-P3 of the sealed rule. Writes `reports/h8r2/c_test_02_result.json`.

    .venv/Scripts/python exploratory/e16_c02_s5_turnover.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TRAILS = Path("D:/tally-forensics-data/trails")
OUT = ROOT / "reports" / "h8r2" / "c_test_02_result.json"


def main() -> None:
    s5 = pd.read_parquet(ROOT / "reports" / "h8r2" / "s1_s6" / "s5.parquet")
    s5 = s5[s5["half"] == "C"]
    boxes = pd.concat([pd.read_parquet(p, columns=["uf", "box"]) for p in sorted(TRAILS.glob("*_boxes.parquet"))])
    boxes = boxes[boxes["box"].isin(s5.index)]
    per, manual, scored = [], 0, 0
    for uf in sorted(boxes["uf"].unique()):
        for rnd in (1, 2):
            v = pd.read_parquet(TRAILS / f"{uf}_r{rnd}.parquet", columns=["box", "n_scores", "score_last", "bio"])
            v = v[v["box"].isin(s5.index) & (v["n_scores"] > 0)]
            if rnd == 2:
                manual += int((v["bio"] == 0).sum())
                scored += len(v)
            g = v.groupby("box")["score_last"]
            per.append(pd.DataFrame({"rnd": rnd, "med": g.median(), "low": g.apply(lambda x: (x <= 12).mean())}))
    x = pd.concat(per).reset_index().pivot(index="box", columns="rnd")
    x.columns = [f"{a}{b}" for a, b in x.columns]
    x = x.join(s5[["flag"]])
    x["d_med"], x["d_low"] = x["med2"] - x["med1"], x["low2"] - x["low1"]
    f, u = x[x["flag"]], x[~x["flag"]]
    moved = f["d_med"].dropna()
    moved = moved[moved != 0]
    up = float((moved > 0).mean())
    low_f, low_u = float(f["d_low"].abs().mean()), float(u["d_low"].abs().mean())
    p3 = manual / scored
    res = {"boxes_tested": int(len(x)), "flagged": int(len(f)), "flagged_moved": int(len(moved)),
           "P1_share_up": up, "P1": 0.35 <= up <= 0.65,
           "P2_abs_dlow_flagged": low_f, "P2_abs_dlow_unflagged": low_u, "P2": low_f >= 2 * low_u,
           "P3_manual_share_r2": p3, "P3": p3 >= 0.99}
    if res["P1"] and res["P2"] and res["P3"]:
        res["decision"] = "explanation supported"
    elif not res["P1"]:
        res["decision"] = "P1 fails: common direction, lead opened"
    elif not res["P3"]:
        res["decision"] = "P3 fails: S5 reopened"
    else:
        res["decision"] = "inconclusive"
    OUT.write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
