"""E24b: rank round-2 boxes against round 2 itself (E24's round-1 yardstick does not fit: round 1 had several
offices per voter, so every round-2 box looks fast against it).

Per feature, a robust z within the UF (median and 1.4826 MAD over the UF's round-2 boxes; UFs differ by whether a
governor run-off was on the ballot). Rates are per vote, so box size does not drive the rank. Paired with the same
box's round 1 only where the comparison holds across rounds: manual share (binomial z) and turnout.
Writes `reports/h8r2/sweep/ranked_r2.csv` and `top_<feature>.csv` (top 50 per feature).

    .venv/Scripts/python exploratory/e24b_rank_r2.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

TRAILS = Path("D:/tally-forensics-data/trails")
OUT = Path(__file__).resolve().parents[1] / "reports" / "h8r2" / "sweep"
Z = 4.0


def rz(x: pd.Series, g: pd.Series) -> pd.Series:
    med = x.groupby(g).transform("median")
    mad = (x - med).abs().groupby(g).transform("median") * 1.4826
    sd = x.groupby(g).transform("std")
    return (x - med) / mad.where(mad > 0, sd).replace(0, np.nan)


def main() -> None:
    f = pd.read_parquet(OUT / "features.parquet")
    r1, r2 = f[f["rnd"] == 1].set_index("box"), f[f["rnd"] == 2].set_index("box")
    d = r2.copy()
    d["votes_r1"], d["manual_share_r1"] = r1["votes"], r1["manual_share"]
    for c in ("min_ge2", "fast_votes", "dup_cycles", "late_votes"):
        d[f"{c}_rate"] = d[c] / d["votes"].clip(lower=1)
    p = (d["manual_share"] * d["votes"] + d["manual_share_r1"] * d["votes_r1"]) / (d["votes"] + d["votes_r1"])
    se = np.sqrt(p * (1 - p) * (1 / d["votes"].clip(lower=1) + 1 / d["votes_r1"].clip(lower=1)))
    d["manual_change_z"] = (d["manual_share"] - d["manual_share_r1"]) / se.replace(0, np.nan)
    d["turnout_ratio"] = d["votes"] / d["votes_r1"].clip(lower=1)
    feats = {"min_ge2_rate": "minutes with 2+ votes, per vote", "fast_votes_rate": "enable-to-vote under 5 s, per vote",
             "dup_cycles_rate": "most repeated timing triple, per vote", "late_votes_rate": "votes after 17:00, per vote",
             "manual_share": "share of manual enablings", "manual_run": "longest run of manual enablings",
             "max_per_min": "most votes in one minute", "fast_run": "run of vote-to-vote cycles under 20 s",
             "turnout_ratio": "round-2 votes / round-1 votes"}
    big = d["votes"] >= 30
    for c in feats:
        d[f"z_{c}"] = np.nan
        d.loc[big, f"z_{c}"] = rz(d.loc[big, c].astype(float), d.loc[big, "uf"])
    d["z_manual_change"] = d["manual_change_z"]
    zc = [f"z_{c}" for c in feats] + ["z_manual_change"]
    d["n_extreme"] = (d[zc] >= Z).sum(axis=1)
    d["max_z"] = d[zc].max(axis=1)
    d["top_feature"] = d[zc].fillna(-np.inf).idxmax(axis=1).str[2:].where(d["max_z"].notna())
    boxes = pd.concat([pd.read_parquet(p, columns=["box", "mun", "zone", "sec", "votes_r2", "n_not_success"])
                       for p in TRAILS.glob("*_boxes.parquet")]).set_index("box")
    d = d.join(boxes[["mun", "zone", "sec"]], how="left")
    d = d.sort_values(["n_extreme", "max_z"], ascending=False)
    d.reset_index().to_csv(OUT / "ranked_r2.csv", index=False)
    for c in zc:
        d.sort_values(c, ascending=False).head(50).reset_index().to_csv(OUT / f"top_{c[2:]}.csv", index=False)
    print("boxes ranked:", int(big.sum()), "| boxes with n features at z >= 4:")
    print(d.loc[big, "n_extreme"].value_counts().sort_index().to_string())
    print("per feature, boxes at z >= 4:")
    print((d.loc[big, zc] >= Z).sum().to_string())
    show = ["uf", "mun", "zone", "sec", "votes", "votes_r1", "n_extreme", "max_z", "top_feature", "min_ge2", "fast_votes",
            "dup_cycles", "late_votes", "manual_share", "manual_share_r1", "manual_run", "max_per_min", "fast_run"]
    print(d[show].head(40).to_string())


if __name__ == "__main__":
    main()
