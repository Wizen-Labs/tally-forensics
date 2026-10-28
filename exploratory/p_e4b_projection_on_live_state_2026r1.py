"""PHASE 2 (private). E4b: run the municipal projections on the final live state of 2026 round 1.

With everything counted they must return the official result (FINDINGS E4).
Run from the repo root after: python -m tally live --election 6257 --once
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import DATA_DIR, INTERIM_DIR, live, project  # noqa: E402

OFFICIAL = {"22": 56_104_503, "13": 53_879_538}


def main() -> None:
    st = live.load_state(DATA_DIR / "live" / "ele2026_e006257")
    ab, mun = st["ab"], st["municipal"]
    r1 = pd.read_parquet(INTERIM_DIR / "sections_2022_t1.parquet")
    r1["CD_MUNICIPIO"] = r1["CD_MUNICIPIO"].astype(int).astype(str)
    x = project.round1_groups(r1, "22", "13")
    base = x.groupby(["SG_UF", "CD_MUNICIPIO"])[project.GROUPS].sum()
    base["n"] = x.groupby(["SG_UF", "CD_MUNICIPIO"]).size()
    agg = ab.merge(mun, on=["SG_UF", "CD_MUNICIPIO"], how="left").fillna(0)
    agg = agg.join(base, on=["SG_UF", "CD_MUNICIPIO"], how="inner")
    agg["A2c"], agg["B2c"] = agg["v_22"], agg["v_13"]
    agg["frac"] = np.where(agg["sections_counted"] >= agg["sections_total"], 1.0,
                           agg["electorate_counted"] / agg["electorate_total"].clip(lower=1))
    Xc = agg[project.GROUPS].to_numpy(float) * agg[["frac"]].to_numpy()
    out_t = project.project_aggregates(agg, Xc, project.Params(bootstrap=0))
    out_s = project.project_swing(agg, Xc)
    truth = 100 * OFFICIAL["22"] / (OFFICIAL["22"] + OFFICIAL["13"])
    print("projection on the final live state (all counted; matched municipalities only):")
    print(f"  transfer model {out_t['share_a']:.4f}% | swing model {out_s['share_a']:.4f}% | "
          f"official A/(A+B) {truth:.4f}%")


if __name__ == "__main__":
    main()
