"""E3 (exploratory): how did TSE publish the 2026 round-1 count live?

TSE's live results site (resultados.tse.jus.br/oficial) exposes, per UF, a section-configuration file
`arquivo-urna/<pleito>/config/<uf>/<uf>-p<pleito>-cs.json` listing every section with a timestamp `da/ha`.
Each section also has an `aux.json` (with its own reception time `dr/hr` and the original box files: bu, rdv, log,
vota). This script downloads the 28 cs files (small) and compares `ha` with the BU reception time `DT_BU_RECEBIDO`
from the bulk bweb data, to measure batching and the lag between reception and publication.
Run from the repo root after `tally build --year 2026`.
"""

import json
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import DATA_DIR, INTERIM_DIR  # noqa: E402
from tally.config import ufs  # noqa: E402

BASE = "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3220/config/{uf}/{uf}-p003220-cs.json"
CACHE = DATA_DIR / "raw" / "2026" / "live_cs"


def fetch_cs() -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    rows = []
    for uf in ufs():
        u = uf.lower()
        path = CACHE / f"{u}-p003220-cs.json"
        if not path.exists():
            req = urllib.request.Request(BASE.format(uf=u), headers={"User-Agent": "tally-forensics/0.3"})
            with urllib.request.urlopen(req, timeout=120) as r:
                path.write_bytes(r.read())
        j = json.loads(path.read_text(encoding="utf-8-sig"))
        for ab in j["abr"]:
            for mu in ab["mu"]:
                for z in mu["zon"]:
                    for s in z["sec"]:
                        rows.append((uf, str(int(mu["cd"])), str(int(z["cd"])), str(int(s["ns"])),
                                     s.get("da"), s.get("ha")))
    cs = pd.DataFrame(rows, columns=["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "da", "ha"])
    cs["published_brt"] = pd.to_datetime(cs["da"] + " " + cs["ha"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    return cs


def main() -> None:
    cs = fetch_cs()
    s = pd.read_parquet(INTERIM_DIR / "sections_2026_t1.parquet",
                        columns=["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "DT_BU_RECEBIDO_BRT"])
    for c in ["CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]:
        s[c] = s[c].astype(int).astype(str)
    m = cs.merge(s, on=["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"], how="left")
    print(f"cs sections: {len(cs):,}; matched to bweb: {m['DT_BU_RECEBIDO_BRT'].notna().mean():.2%}; "
          f"with publication time: {cs['published_brt'].notna().mean():.2%}")
    m["lag_min"] = (m["published_brt"] - m["DT_BU_RECEBIDO_BRT"]).dt.total_seconds() / 60
    home = m[m["SG_UF"] != "ZZ"]
    print("\nlag reception -> cs timestamp (min), Brazil:")
    print(home["lag_min"].describe(percentiles=[.05, .25, .5, .75, .95]).round(1).to_string())
    print("\ndistinct cs timestamps (seconds):", home["published_brt"].nunique(),
          "| distinct reception timestamps:", home["DT_BU_RECEBIDO_BRT"].nunique())

    pub = home["published_brt"].dt.floor("min").value_counts().sort_index()
    day = pd.Timestamp("2026-10-04")
    rng = pd.date_range(day + pd.Timedelta("17:00:00"), day + pd.Timedelta("23:00:00"), freq="min")
    pub = pub.reindex(rng, fill_value=0)
    print("\nminutes 17:00-23:00 with any cs timestamp:", int((pub > 0).sum()), "of", len(pub))
    burst = pub[pub > 0]
    print("largest cs batches (minute: sections):", {f"{t:%H:%M}": int(v) for t, v in burst.nlargest(12).items()})
    cum = home["published_brt"].sort_values()
    for hhmm in ["18:00", "18:30", "19:00", "19:15", "19:30", "20:00", "20:08", "20:30", "21:00"]:
        t = day + pd.Timedelta(hhmm + ":00")
        print(f"  by {hhmm}: published {100 * (cum <= t).mean():5.1f}%  | received "
              f"{100 * (home['DT_BU_RECEBIDO_BRT'] <= t).mean():5.1f}%")
    gap = home[(home["published_brt"] >= day + pd.Timedelta("19:00:00"))
               & (home["published_brt"] < day + pd.Timedelta("20:10:00"))]
    print("\ncs timestamps between 19:00 and 20:10 by minute:",
          gap["published_brt"].dt.strftime("%H:%M").value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
