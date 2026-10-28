"""PHASE 2 (lab). Builds the 2022 governor sections (office 3) for round 1 and round 2 from the bweb files already
downloaded, and lists the states that had a governor run-off. These run-offs are extra backtests for the
presidential run-off projection (FINDINGS P6).
Run from the repo root.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import INTERIM_DIR, fetch, load  # noqa: E402
from tally.config import ufs  # noqa: E402


def main() -> None:
    states = [u for u in ufs() if u not in ("ZZ", "DF")] + ["DF"]
    for turn in (1, 2):
        paths = [fetch.raw_path(2022, turn, uf) for uf in states]
        load.build([p for p in paths if p.exists()], 2022, turn, office_code="3")
    r2 = pd.read_parquet(INTERIM_DIR / "sections_2022_t2_c3.parquet")
    vcols = [c for c in r2.columns if c.startswith("v_") and c[2:].isdigit()]
    tot = r2.groupby("SG_UF")[vcols].sum()
    out = []
    for uf, row in tot.iterrows():
        top = row[row > 0].sort_values(ascending=False)
        if len(top) >= 2:
            out.append({"SG_UF": uf, "A": top.index[0][2:], "B": top.index[1][2:], "sections": int((r2["SG_UF"] == uf).sum())})
    runoffs = pd.DataFrame(out)
    runoffs.to_csv(INTERIM_DIR / "governor_runoffs_2022.csv", index=False)
    print(runoffs.to_string(index=False))


if __name__ == "__main__":
    main()
