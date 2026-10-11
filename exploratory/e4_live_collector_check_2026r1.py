"""E4: end-to-end check of the live collector against 2026 round 1 (election 6257), presidential race only.

1. Rebuild the state from the archive alone (`tally.live.load_state`).
2. Reconcile: municipal files summed == national file == official totals; per municipality, live votes == sum of the
   section BUs (bweb) and live section counts == bweb section counts.
Run from the repo root after: python -m tally live --election 6257 --once
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import DATA_DIR, INTERIM_DIR, live  # noqa: E402

OFFICIAL = {"22": 56_104_503, "13": 53_879_538}


def main() -> None:
    st = live.load_state(DATA_DIR / "live" / "ele2026_e006257")
    mun, ab, br = st["municipal"], st["ab"], st["br"]
    print(f"state: {len(ab):,} municipalities in progress files, {len(mun):,} municipal result files, "
          f"{len(st['uf'])} UF files, national file generated {br['generated']}")

    for nr in ("22", "13"):
        print(f"  #{nr}: municipal sum {int(mun['v_' + nr].sum()):,} | national file {br['votes'][nr]:,} | "
              f"official {OFFICIAL[nr]:,} | diff municipal-official {int(mun['v_' + nr].sum()) - OFFICIAL[nr]:+,}")

    bw = pd.read_parquet(INTERIM_DIR / "sections_2026_t1.parquet")
    bw["CD_MUNICIPIO"] = bw["CD_MUNICIPIO"].astype(int).astype(str)
    g = bw.groupby(["SG_UF", "CD_MUNICIPIO"]).agg(bu_22=("v_22", "sum"), bu_13=("v_13", "sum"),
                                                   bu_sections=("NR_SECAO", "size")).reset_index()
    m = mun.merge(g, on=["SG_UF", "CD_MUNICIPIO"], how="outer", indicator=True)
    m = m.merge(ab[["SG_UF", "CD_MUNICIPIO", "sections_total", "sections_counted"]], on=["SG_UF", "CD_MUNICIPIO"],
                how="left")
    print(f"\nmunicipalities: both {int((m['_merge'] == 'both').sum()):,}, live only "
          f"{int((m['_merge'] == 'left_only').sum())}, bweb only {int((m['_merge'] == 'right_only').sum())}")
    b = m[m["_merge"] == "both"]
    for nr in ("22", "13"):
        bad = b[b["v_" + nr] != b["bu_" + nr]]
        print(f"  #{nr}: municipalities where live != sum of BUs: {len(bad)}")
    sec_bad = b[b["sections_total"] != b["bu_sections"]]
    print(f"  section counts: progress file != bweb sections in {len(sec_bad)} municipalities "
          f"(aggregated sections count once in bweb; see DS_SECOES_AGREGADAS)")


if __name__ == "__main__":
    main()
