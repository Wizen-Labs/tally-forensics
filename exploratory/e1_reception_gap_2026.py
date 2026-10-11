"""E1 (exploratory, NOT pre-registered): the 2026 reception gap.

Context: the confirmatory run (FINDINGS, 2026) showed that no BU carries a TSE reception time between 19:31:50 and
19:59:22 BRT, in any UF. This script:
1. prints per-minute receptions for 2026 and, as the reference, 2022;
2. tests whether the sections received during the slowdown, in the catch-up burst and in the slow tail differ from
   their own polling-location siblings, using the same adjusted test as H1.

Results are exploratory: they can motivate a pre-registered test for round 2, never a confirmatory claim.
Run: python exploratory/e1_reception_gap_2026.py  (from the repo root, after `tally build` for 2022 and 2026)
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import INTERIM_DIR, temporal  # noqa: E402
from tally.analyze import prepare  # noqa: E402
from tally.config import analysis  # noqa: E402

DAYS = {2026: pd.Timestamp("2026-10-04"), 2022: pd.Timestamp("2022-10-02")}
WINDOWS = [("slowdown 19:21-19:32", "19:21", "19:32"),
           ("catch-up burst 19:59-20:03", "19:59", "20:03"),
           ("slow tail 20:03-20:30", "20:03", "20:30")]


def per_minute(year: int) -> pd.Series:
    s = pd.read_parquet(INTERIM_DIR / f"sections_{year}_t1.parquet")
    t = s.loc[s["SG_UF"] != "ZZ", "DT_BU_RECEBIDO_BRT"].dt.floor("min").value_counts()
    rng = pd.date_range(DAYS[year] + pd.Timedelta("19:00:00"), DAYS[year] + pd.Timedelta("20:30:00"), freq="min")
    return t.reindex(rng, fill_value=0)


def main() -> None:
    for year in (2026, 2022):
        m = per_minute(year)
        zero = m[m == 0]
        print(f"\n{year}: receptions per minute 19:00-20:30 BRT (min {m.min()}, median {int(m.median())})")
        print("  zero-reception minutes:", f"{zero.index[0]:%H:%M}-{zero.index[-1]:%H:%M} ({len(zero)})"
              if len(zero) else "none")

    cfg = analysis()
    s = prepare(pd.read_parquet(INTERIM_DIR / "sections_2026_t1.parquet"), 2026)
    h = s[(s["SG_UF"] != "ZZ") & (s["CD_TIPO_URNA"] == 1)]
    rec = h["DT_BU_RECEBIDO_BRT"]
    print("\nlast reception before the gap:", rec[rec < DAYS[2026] + pd.Timedelta("19:45:00")].max())
    print("first reception after the gap:", rec[rec >= DAYS[2026] + pd.Timedelta("19:35:00")].min())
    print("cumulative % of sections received before the gap:",
          round(100 * (rec < DAYS[2026] + pd.Timedelta("19:32:00")).mean(), 2))

    print("\nwindow                         metric              locations     in   effect      p")
    for label, a, b in WINDOWS:
        start, end = temporal.window_bounds(DAYS[2026], a, b)
        for metric in ("margin_resid", "turnout_resid"):
            r = temporal.window_test(h, start, end, metric, cfg["permutations"], cfg["random_seed"], adjust=True)
            print(f"{label:30s} {r['metric']:18s} {r['informative_locations']:9,d} {r['n_in']:6,d} "
                  f"{100 * r['effect']:+7.3f}pp {r['p_value']:.4f}")


if __name__ == "__main__":
    main()
