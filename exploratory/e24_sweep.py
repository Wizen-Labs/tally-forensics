"""E24: exploratory sweep of every box log, both halves, both rounds, maximum sensitivity (author's decision,
2026-10-28: search for every possible anomaly first, focused checks afterwards). No seal, no thresholds to pass:
every box gets its features and its rank; round 1 is context, never a filter.

Features per box and round (times in seconds from the trails, E12):
- max_per_min, min_ge2: most votes in one clock minute, minutes with 2 or more votes;
- fast_votes: votes with enabling-to-vote under 5 s; fast_cycles: vote-to-vote under 15 s;
- fast_run: longest run of consecutive vote-to-vote cycles under 20 s;
- manual_share, manual_run: share of non-biometric enablings, longest run of consecutive ones;
- order_errors: vote computed before enabling, or enabling before identification;
- late_votes: votes after 17:00 on the box clock;
- dup_cycles: most repeated identical (identification, enabling, vote) duration triple within the box.
Writes `reports/h8r2/sweep/features.parquet` (box x round) and `ranked.csv` (round 2, with the round-1 value of the
same box and, per feature, the share of round-1 boxes nationally with a value at least as high).

    .venv/Scripts/python exploratory/e24_sweep.py [uf ...]
"""
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

TRAILS = Path("D:/tally-forensics-data/trails")
OUT = Path(__file__).resolve().parents[1] / "reports" / "h8r2" / "sweep"
COLS = ["box", "idx", "t_id", "t_enabled", "t_computed", "bio"]
FEATS = ["votes", "max_per_min", "min_ge2", "fast_votes", "fast_cycles", "fast_run", "manual_share", "manual_run",
         "order_errors", "late_votes", "dup_cycles"]


def longest_run(flag: np.ndarray, box: np.ndarray) -> np.ndarray:
    """Per row: length of the run of True ending at that row, restarting at each box."""
    c = np.cumsum(flag)
    new = np.r_[True, box[1:] != box[:-1]]
    base = np.maximum.accumulate(np.where(~flag, c, np.where(new, c - 1, -1)))
    return c - base


def features(v: pd.DataFrame) -> pd.DataFrame:
    v = v.sort_values(["box", "t_computed", "idx"], kind="stable").reset_index(drop=True)
    box = v["box"].to_numpy()
    tc = v["t_computed"].to_numpy()
    same = np.r_[False, box[1:] == box[:-1]]
    cyc = np.where(same, np.r_[0, np.diff(tc)], 10 ** 6)
    v["fast_vote"] = (v["t_computed"] - v["t_enabled"]).between(0, 4)
    v["fast_cycle"] = cyc < 15
    v["cyc20_run"] = longest_run(cyc < 20, box)
    manual = (v["bio"] != 1).to_numpy()
    v["manual"] = manual
    v["manual_run"] = longest_run(manual, box)
    v["order_error"] = (v["t_computed"] < v["t_enabled"]) | ((v["t_enabled"] < v["t_id"]) & (v["t_id"] > 0))
    v["late"] = v["t_computed"] >= 17 * 3600
    v["minute"] = v["t_computed"] // 60
    g = v.groupby("box")
    f = pd.DataFrame({"votes": g.size(), "fast_votes": g["fast_vote"].sum(), "fast_cycles": g["fast_cycle"].sum(),
                      "fast_run": g["cyc20_run"].max(), "manual_share": g["manual"].mean(),
                      "manual_run": g["manual_run"].max(), "order_errors": g["order_error"].sum(),
                      "late_votes": g["late"].sum()})
    pm = v.groupby(["box", "minute"]).size()
    f["max_per_min"] = pm.groupby(level=0).max()
    f["min_ge2"] = (pm >= 2).groupby(level=0).sum()
    trip = v.assign(a=v["t_enabled"] - v["t_id"], b=v["t_computed"] - v["t_enabled"])
    f["dup_cycles"] = trip.groupby(["box", "a", "b"]).size().groupby(level=0).max()
    return f.reset_index()


def one(args) -> pd.DataFrame:
    uf, rnd = args
    pf = pq.ParquetFile(TRAILS / f"{uf}_r{rnd}.parquet")
    parts, carry = [], None
    for i in range(pf.num_row_groups):              # row groups are sorted by box; a box may straddle two groups
        t = pf.read_row_group(i, columns=COLS).to_pandas()
        if carry is not None:
            t = pd.concat([carry, t], ignore_index=True)
        last = t["box"].iloc[-1]
        carry = t[t["box"] == last]
        t = t[t["box"] != last]
        if len(t):
            parts.append(features(t))
    if carry is not None and len(carry):
        parts.append(features(carry))
    f = pd.concat(parts, ignore_index=True)
    f["uf"], f["rnd"] = uf, rnd
    return f


def main() -> None:
    ufs = sys.argv[1:] or sorted({p.stem.split("_")[0] for p in TRAILS.glob("*_r2.parquet")})
    OUT.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(6) as ex:
        f = pd.concat(ex.map(one, [(u, r) for u in ufs for r in (1, 2)]), ignore_index=True)
    f.to_parquet(OUT / "features.parquet")
    boxes = pd.concat([pd.read_parquet(TRAILS / f"{u}_boxes.parquet", columns=["box", "uf", "mun", "zone", "sec"])
                       for u in ufs])
    r1, r2 = f[f["rnd"] == 1].set_index("box"), f[f["rnd"] == 2].set_index("box")
    out = r2[FEATS].join(r1[FEATS], rsuffix="_r1")
    for c in FEATS[1:]:
        ref = np.sort(r1[c].dropna().to_numpy())
        # tail: share of round-1 boxes (national) with a value at least as high; manual_share and late_votes too
        out[f"{c}_tail_r1"] = 1 - np.searchsorted(ref, out[c].to_numpy(), side="left") / len(ref)
    tail = out[[f"{c}_tail_r1" for c in FEATS[1:]]]
    out["n_extreme"] = (tail <= 0.001).sum(axis=1)
    out["min_tail"] = tail.min(axis=1)
    out = out.join(boxes.set_index("box")).sort_values(["n_extreme", "min_tail"], ascending=[False, True])
    out.reset_index().to_csv(OUT / "ranked.csv", index=False)
    print(out["n_extreme"].value_counts().sort_index().to_string())
    print(out.head(30)[["uf", "mun", "zone", "sec", "n_extreme"] + FEATS].to_string())


if __name__ == "__main__":
    main()
