"""E5 (exploratory): was the 19:32-19:58 reception gap the only one on 2026-10-04?

Two timelines, Brazil only, from the first reception until 99.5% received:
1. BU reception (DT_BU_RECEBIDO, bweb): every run of >= 2 consecutive minutes with zero receptions, and every minute
   whose count is < 10% of the median of the surrounding 30 minutes (a "dip").
2. Municipal totalisation (the `ht` time in the 28 progress files `ab`): runs of >= 2 minutes in which no
   municipality was completed.
The same scan is run on the 2022 round-1 reception data, as the reference.
Run from the repo root (needs the bweb build for 2026 r1 and 2022 r1, and the live archive of election 6257).
"""

import gzip
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import DATA_DIR, INTERIM_DIR  # noqa: E402


def zero_runs(per_min: pd.Series, min_len: int) -> list[tuple[str, str, int]]:
    runs, start = [], None
    for ts, n in per_min.items():
        if n == 0 and start is None:
            start = ts
        elif n > 0 and start is not None:
            k = int((ts - start).total_seconds() // 60)
            if k >= min_len:
                runs.append((f"{start:%H:%M}", f"{ts:%H:%M}", k))
            start = None
    return runs


def timeline(times: pd.Series, until: float = 0.995) -> pd.Series:
    t = times.dropna().sort_values()
    end = t.iloc[int(until * (len(t) - 1))]
    rng = pd.date_range(t.iloc[0].floor("min"), end.floor("min"), freq="min")
    return t.dt.floor("min").value_counts().reindex(rng, fill_value=0)


def dips(per_min: pd.Series) -> list[tuple[str, int, int]]:
    base = per_min.rolling(31, center=True, min_periods=10).median()
    m = per_min[(per_min < 0.1 * base) & (base > 200)]
    return [(f"{ts:%H:%M}", int(v), int(base[ts])) for ts, v in m.items()]


def reception(year: int) -> pd.Series:
    s = pd.read_parquet(INTERIM_DIR / f"sections_{year}_t1.parquet", columns=["SG_UF", "DT_BU_RECEBIDO_BRT"])
    return timeline(s.loc[s["SG_UF"] != "ZZ", "DT_BU_RECEBIDO_BRT"])


def municipal_totalisation() -> pd.Series:
    arch = DATA_DIR / "live" / "ele2026_e006257"
    latest = {}
    for line in open(arch / "fetch_log.jsonl", encoding="utf-8"):
        e = json.loads(line)
        if "sha256" in e and e["url"].endswith("-ab.json"):
            latest[e["url"]] = e["sha256"]
    rows = []
    for url, sha in latest.items():
        uf = url.rsplit("/", 2)[-2].upper()
        if uf in ("BR", "ZZ"):
            continue
        j = json.loads(gzip.decompress((arch / "blobs" / f"{sha}.json.gz").read_bytes()).decode("utf-8-sig"))
        rows += [(uf, str(int(a["cdabr"])), f"{a['dt']} {a['ht']}") for a in j["abr"]
                 if a.get("tpabr") == "mun" and a.get("ht")]
    ab = pd.DataFrame(rows, columns=["SG_UF", "CD_MUNICIPIO", "ht"])
    ab["ht"] = pd.to_datetime(ab["ht"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    # `ht` is the municipality's LOCAL clock (UTC-4 municipalities lag BRT by 1 h); convert with the offset that
    # tally.load infers per municipality from the ballot boxes' opening hour.
    s = pd.read_parquet(INTERIM_DIR / "sections_2026_t1.parquet", columns=["SG_UF", "CD_MUNICIPIO", "tz_offset_h"])
    s["CD_MUNICIPIO"] = s["CD_MUNICIPIO"].astype(int).astype(str)
    off = s.groupby(["SG_UF", "CD_MUNICIPIO"])["tz_offset_h"].first()
    ab = ab.join(off, on=["SG_UF", "CD_MUNICIPIO"])
    ab["ht_brt"] = ab["ht"] + pd.to_timedelta(ab["tz_offset_h"].fillna(0), unit="h")
    return timeline(ab["ht_brt"])


def main() -> None:
    for label, series in [("2026 r1 BU reception", reception(2026)), ("2022 r1 BU reception", reception(2022)),
                          ("2026 r1 municipal totalisation (ab ht)", municipal_totalisation())]:
        print(f"\n== {label}: {series.index[0]:%H:%M}-{series.index[-1]:%H:%M}, median {int(series.median())}/min")
        print("  zero-runs >= 2 min:", zero_runs(series, 2) or "none")
        d = dips(series)
        print(f"  dips (< 10% of local median): {len(d)}", d[:15])


if __name__ == "__main__":
    main()
