"""C4: calibration of the round-2 forensic protocol on the 2022 run-off (no freeze is known to have happened there).

- H3 calibration: nationwide reception gaps of 5 minutes or more before 95% of sections were received.
- H1 calibration: the bin scan (10-minute bins, adjusted within-location margin test). How many bins reject at the
  Bonferroni threshold, and at the nominal 0.01? A valid test should give about 0 and about 1% respectively.
Run from the repo root after `tally build --year 2022 --turn 2`.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import INTERIM_DIR, REPORTS_DIR, temporal  # noqa: E402
from tally.analyze import prepare  # noqa: E402

BIN, UNTIL, PERM, SEED, ALPHA = 10, 0.99, 2000, 20261025, 0.01


def main() -> None:
    s = prepare(pd.read_parquet(INTERIM_DIR / "sections_2022_t2.parquet"), 2022)
    h = s[(s["SG_UF"] != "ZZ") & (s["CD_TIPO_URNA"] == 1)]
    gaps = temporal.reception_gaps(h)
    print("H3 calibration, 2022 run-off reception gaps >= 5 min before 95% received:", gaps or "none")
    scan = temporal.scan_bins(h, BIN, UNTIL, "margin_resid", PERM, SEED, adjust=True)
    k = len(scan)
    scan["reject_bonferroni"] = scan["p_value"] < ALPHA / k
    scan["reject_nominal"] = scan["p_value"] < ALPHA
    out = REPORTS_DIR / "calibration_round2_2022"
    out.mkdir(parents=True, exist_ok=True)
    scan.to_csv(out / "bin_scan.csv", index=False)
    (out / "summary.json").write_text(json.dumps({
        "bins": k, "bonferroni_threshold": ALPHA / k, "reject_bonferroni": int(scan["reject_bonferroni"].sum()),
        "reject_nominal": int(scan["reject_nominal"].sum()), "min_p": float(scan["p_value"].min()),
        "reception_gaps": gaps}, indent=2), encoding="utf-8")
    print(scan[["start_brt", "informative_locations", "n_in", "effect", "p_value"]].assign(
        effect=lambda d: (100 * d["effect"]).round(3)).to_string(index=False))
    print(f"\nbins {k}; reject at Bonferroni ({ALPHA / k:.5f}): {int(scan['reject_bonferroni'].sum())}; "
          f"reject at nominal 0.01: {int(scan['reject_nominal'].sum())}")


if __name__ == "__main__":
    main()
