"""E14 (H8r2 §3): S7 software detector on every round-2 log, both halves (S7 is structural; allowed on C).

Reads the E12 box tables, applies the frozen `signatures.s7_software` and writes every listed log with its half.

    .venv/Scripts/python exploratory/e14_s7_software.py [--trails D:/tally-forensics-data/trails]
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tally import signatures as sg

OUT = Path(__file__).resolve().parents[1] / "reports" / "h8r2"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trails", default="D:/tally-forensics-data/trails")
    a = ap.parse_args()
    b = pd.concat([pd.read_parquet(p) for p in sorted(Path(a.trails).glob("*_boxes.parquet"))], ignore_index=True)
    half = sg.split_ufs(sorted(b["uf"].unique()))
    b["half"] = b["uf"].str.upper().map(half)
    s7 = sg.s7_software(b)
    s7.drop(columns=["error"]).to_csv(OUT / "s7_software.csv", index=False)
    print(f"{len(b):,} logs; {len(s7):,} listed by S7")
    print(b.groupby("model").agg(logs=("box", "size"), versions=("version", "nunique"),
                                 filesets=("fileset", "nunique")).to_string())
    why = pd.DataFrame({"differs": s7["differs"], "not_success": s7["n_not_success"] > 0,
                        "no_check": s7["n_checks"] == 0, "half": s7["half"]})
    print(why.groupby("half")[["differs", "not_success", "no_check"]].sum().to_string())


if __name__ == "__main__":
    main()
