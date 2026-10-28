"""E2 (exploratory): what do the first 2% / 5% of received sections look like?

Question for the round-2 projection: after 2-5% of sections, how representative is the counted set, and how much of
each minor candidate's vote has already been observed (which is what identifies its transfer)?
Run from the repo root: python exploratory/e2_early_coverage_2026.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import INTERIM_DIR  # noqa: E402

MINOR = {"70": "Cury", "14": "Renan Santos", "55": "Caiado", "30": "Zema"}


def main() -> None:
    s = pd.read_parquet(INTERIM_DIR / "sections_2026_t1.parquet")
    s = s[s["SG_UF"] != "ZZ"].sort_values("DT_BU_RECEBIDO_BRT")
    vcols = [c for c in s.columns if c.startswith("v_") and c[2:].isdigit()]
    s["valid"] = s[vcols].sum(axis=1)
    s["others"] = s["valid"] - s["v_22"] - s["v_13"]
    rank = pd.Series(range(1, len(s) + 1), index=s.index) / len(s)

    for cut in (0.02, 0.05, 0.10):
        e = s[rank <= cut]
        print(f"\n=== first {cut:.0%} of sections: {len(e):,}, received by {e['DT_BU_RECEBIDO_BRT'].max():%H:%M} BRT")
        print(f"  UFs with >= 30 sections: {(e['SG_UF'].value_counts() >= 30).sum()} of 27")
        tot = lambda d, c: 100 * d[c].sum() / d["valid"].sum()  # noqa: E731
        print(f"  shares in counted set : Flavio {tot(e, 'v_22'):.2f}  Lula {tot(e, 'v_13'):.2f}  "
              f"others {tot(e, 'others'):.2f}")
        print(f"  shares, final         : Flavio {tot(s, 'v_22'):.2f}  Lula {tot(s, 'v_13'):.2f}  "
              f"others {tot(s, 'others'):.2f}")
        print("  share of each candidate's national vote already observed:")
        for nr, name in MINOR.items():
            col = "v_" + nr
            print(f"    {name:13s} {100 * e[col].sum() / s[col].sum():5.1f}%   "
                  f"({e[col].sum():,} votes; top UF in counted set: {e.groupby('SG_UF')[col].sum().idxmax()})")
        reg = e["SG_UF"].value_counts(normalize=True).head(6).mul(100).round(1).to_dict()
        print("  largest UFs in counted set (% of sections):", reg)


if __name__ == "__main__":
    main()
