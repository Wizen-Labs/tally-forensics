"""E20: sections whose minutes (atas da mesa receptora, both rounds) are requested for the S5 lead (C-02).

Draws, with a fixed seed, 30 of the 1,100 half-C sections flagged by S5 and, for each, one control: an S5-tested,
unflagged section of the same UF, municipality and zone, with the nearest section number. Uses only the E15 S5
flags and the box table (no new half-C field is read). Writes `reports/h8r2/s5_minutes_request.csv`.

    .venv/Scripts/python exploratory/e20_s5_minutes_sample.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TRAILS = Path("D:/tally-forensics-data/trails")
SEED, N = 20261027, 30


def main() -> None:
    s5 = pd.read_parquet(ROOT / "reports" / "h8r2" / "s1_s6" / "s5.parquet")
    s5 = s5[s5["half"] == "C"]
    b = pd.concat([pd.read_parquet(p, columns=["uf", "mun", "zone", "sec", "box"])
                   for p in sorted(TRAILS.glob("*_boxes.parquet"))])
    t = b[b["box"].isin(s5.index)].join(s5["flag"], on="box")
    flagged = t[t["flag"]].sample(N, random_state=SEED)
    pool = t[~t["flag"]]
    rows = []
    for k, (_, r) in enumerate(flagged.sort_values(["uf", "mun", "zone", "sec"]).iterrows(), 1):
        same = pool[(pool["uf"] == r["uf"]) & (pool["mun"] == r["mun"]) & (pool["zone"] == r["zone"])]
        rows.append({"pair": k, "role": "flagged", **r[["uf", "mun", "zone", "sec"]].to_dict()})
        if len(same):
            c = same.iloc[(same["sec"] - r["sec"]).abs().argsort().iloc[0]]
            rows.append({"pair": k, "role": "control", **c[["uf", "mun", "zone", "sec"]].to_dict()})
        else:
            rows.append({"pair": k, "role": "control", "uf": r["uf"], "mun": r["mun"], "zone": r["zone"],
                         "sec": None})
    out = pd.DataFrame(rows)
    out["uf"] = out["uf"].str.upper()
    out.to_csv(ROOT / "reports" / "h8r2" / "s5_minutes_request.csv", index=False)
    print(out.to_string(index=False))
    print(out[out["role"] == "flagged"]["uf"].value_counts().to_dict())


if __name__ == "__main__":
    main()
