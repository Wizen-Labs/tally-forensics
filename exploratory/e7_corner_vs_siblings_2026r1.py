"""E7 (exploratory): are the "ballot-stuffing corner" sections out of line with their own polling-location siblings?

For each candidate, take the sections with turnout >= T and candidate share >= S (corner). For each one, compute the
pooled share and turnout of the OTHER sections in the same polling location (siblings). Small-scale stuffing would
show as corner sections whose siblings are much lower; a genuinely cohesive community shows siblings that are just
as high. 2022 is the reference. Thresholds: 95/95 (strict) and 90/90 (wider).
Run from the repo root after the 2022 and 2026 round-1 builds.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import INTERIM_DIR  # noqa: E402
from tally.load import add_shares  # noqa: E402
from tally.residuals import LOCATION  # noqa: E402


def load(year: int) -> pd.DataFrame:
    s = pd.read_parquet(INTERIM_DIR / f"sections_{year}_t1.parquet")
    s = add_shares(s[(s["SG_UF"] != "ZZ") & (s["CD_TIPO_URNA"] == 1)], "22", "13")
    return s[s["valid"] >= 30]


def corner_report(s: pd.DataFrame, col: str, votes: str, t: float, sh: float) -> dict:
    g = s.groupby(LOCATION)
    tot_v, tot_valid = g[votes].transform("sum"), g["valid"].transform("sum")
    tot_c, tot_apt = g["QT_COMPARECIMENTO"].transform("sum"), g["QT_APTOS"].transform("sum")
    n = g["valid"].transform("size")
    s = s.assign(sib_share=(tot_v - s[votes]) / (tot_valid - s["valid"]),
                 sib_turnout=(tot_c - s["QT_COMPARECIMENTO"]) / (tot_apt - s["QT_APTOS"]), n_loc=n)
    c = s[(s["turnout"] >= t) & (s[col] >= sh)]
    with_sib = c[c["n_loc"] > 1]
    far = with_sib[(with_sib[col] - with_sib["sib_share"]) > 0.20]
    return {"corner": len(c), "with_siblings": len(with_sib), "alone_in_location": int((c["n_loc"] == 1).sum()),
            "median_own_share": round(100 * c[col].median(), 1),
            "median_sibling_share": round(100 * with_sib["sib_share"].median(), 1) if len(with_sib) else None,
            "median_sibling_turnout": round(100 * with_sib["sib_turnout"].median(), 1) if len(with_sib) else None,
            "own_minus_siblings_gt_20pp": len(far),
            "far_examples": far[["SG_UF", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", col, "sib_share"]]
            .assign(**{col: lambda d: (100 * d[col]).round(1), "sib_share": lambda d: (100 * d["sib_share"]).round(1)})
            .head(10).to_dict("records")}


def main() -> None:
    for year in (2026, 2022):
        s = load(year)
        for t, sh in ((0.95, 0.95), (0.90, 0.90)):
            for col, votes, name in (("share_a", "votes_a", "#22"), ("share_b", "votes_b", "#13")):
                r = corner_report(s, col, votes, t, sh)
                ex = r.pop("far_examples")
                print(f"{year} {name} corner turnout>={t:.0%} share>={sh:.0%}: {r}")
                for e in ex:
                    print("     out of line:", e)


if __name__ == "__main__":
    main()
