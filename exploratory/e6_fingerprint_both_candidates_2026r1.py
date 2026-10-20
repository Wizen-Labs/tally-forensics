"""E6 (exploratory): election fingerprint (Klimek et al. 2012) for BOTH leading candidates, 2026 round 1.

The pre-registered report plots candidate A only. Ballot stuffing in favour of candidate B would show as a cluster at
high turnout and high B share, so B gets its own panel instead of relying on the mirror image. The script also reports
the share of sections in the extreme corner (turnout >= 95% and candidate share >= 95%) for each candidate, with
2022 as the reference.
Run from the repo root after `tally build --year 2026` and `--year 2022`.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import INTERIM_DIR, REPORTS_DIR  # noqa: E402
from tally.load import add_shares  # noqa: E402

OUT = REPORTS_DIR / "2026_t1_20261011-133033" / "E6_fingerprint_both_candidates.png"


def sections(year: int, nr_a: str, nr_b: str) -> pd.DataFrame:
    s = pd.read_parquet(INTERIM_DIR / f"sections_{year}_t1.parquet")
    s = add_shares(s[(s["SG_UF"] != "ZZ") & (s["CD_TIPO_URNA"] == 1)], nr_a, nr_b)
    return s[s["valid"] >= 30]


def main() -> None:
    s = sections(2026, "22", "13")
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
    for ax, col, name in [(axes[0], "share_a", "Flavio Bolsonaro"), (axes[1], "share_b", "Lula")]:
        h = ax.hist2d(s["turnout"] * 100, s[col] * 100, bins=[100, 100], range=[[40, 100], [0, 100]],
                      cmap="viridis", cmin=1)
        ax.set_title(f"{name}: share of valid votes vs turnout")
        ax.set_xlabel("turnout (%)")
        ax.add_patch(plt.Rectangle((95, 95), 5, 5, fill=False, ec="red", lw=1.5))
    axes[0].set_ylabel("candidate share of valid votes (%)")
    fig.colorbar(h[3], ax=axes, label="sections")
    fig.suptitle("Election fingerprint, 2026 round 1 (red box: the ballot-stuffing corner)")
    fig.savefig(OUT, dpi=130, bbox_inches="tight")
    print(f"figure -> {OUT}")

    for year, (a, b) in [(2026, ("22", "13")), (2022, ("22", "13"))]:
        d = sections(year, a, b)
        for col, name in [("share_a", f"#{a}"), ("share_b", f"#{b}")]:
            corner = ((d["turnout"] >= 0.95) & (d[col] >= 0.95)).sum()
            r = d[["turnout", col]].corr().iloc[0, 1]
            print(f"{year} {name}: sections in corner (turnout>=95% & share>=95%): {corner} of {len(d):,} | "
                  f"corr(turnout, share) = {r:+.3f}")


if __name__ == "__main__":
    main()
