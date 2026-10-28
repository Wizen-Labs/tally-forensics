"""E12 (H8r2 §1): per-voter trails and box records of every round-2 log, for S1-S7.

Reads each raw log once with the frozen `signatures.box_record` and writes, per UF:
  - `<out>/<uf>_r1.parquet`, `<out>/<uf>_r2.parquet`: voter tables (VOTER_COLS plus "box");
  - `<out>/<uf>_boxes.parquet`: one row per log (box id, section, sha12, S7 features, vote and incomplete counts).
The box id is a global integer; the section and log are in the box table. No personal data: `trails` replaces the
poll workers' numbers by a per-box index while reading.

    .venv/Scripts/python exploratory/e12_trails_2026r2.py [--out D:/tally-forensics-data/trails] [--procs 6]
"""
import argparse
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tally import DATA_DIR
from tally import signatures as sg

SRC = DATA_DIR / "urna_logs" / "p3221" / "raw"
NAME = re.compile(r"o03221([a-z]{2})(\d{5})(\d{4})(\d{4})-log\.jez\.([0-9a-f]{12})$")


def one(path: str) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    m = NAME.search(path)
    rec = {"uf": m[1], "mun": int(m[2]), "zone": int(m[3]), "sec": int(m[4]), "sha12": m[5]}
    try:
        voters, box = sg.box_record(Path(path).read_bytes())
    except Exception as e:                       # unreadable log: listed, not dropped silently
        empty = pd.DataFrame(columns=sg.VOTER_COLS, dtype="int32")
        return {**rec, "error": repr(e)[:200]}, empty, empty
    return {**rec, **box, "error": ""}, voters[1], voters[2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="D:/tally-forensics-data/urna_logs_full")
    ap.add_argument("--out", default="D:/tally-forensics-data/trails")
    ap.add_argument("--procs", type=int, default=6)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for d in (SRC, Path(a.dest)):
        for p in d.glob("*/o03221*-log.jez.*"):
            files.setdefault(p.name, str(p))
    by_uf = {}
    for name, p in sorted(files.items()):
        by_uf.setdefault(NAME.search(name)[1], []).append(p)
    print(f"{len(files):,} logs in {len(by_uf)} UFs", flush=True)
    box_id = 0
    with ProcessPoolExecutor(a.procs) as ex:
        for uf, paths in by_uf.items():
            if (out / f"{uf}_boxes.parquet").exists():
                box_id += len(pd.read_parquet(out / f"{uf}_boxes.parquet"))
                print(f"{uf}: already done", flush=True)
                continue
            boxes, r1, r2 = [], [], []
            for rec, v1, v2 in ex.map(one, paths, chunksize=100):
                rec["box"] = box_id
                boxes.append(rec)
                r1.append(v1.assign(box=box_id))
                r2.append(v2.assign(box=box_id))
                box_id += 1
            for rnd, parts in ((1, r1), (2, r2)):
                pd.concat(parts, ignore_index=True).astype("int32").to_parquet(out / f"{uf}_r{rnd}.parquet")
            b = pd.DataFrame(boxes)
            b.to_parquet(out / f"{uf}_boxes.parquet")       # written last: marks the UF as done
            print(f"{uf}: {len(b):,} logs, {b['votes_r2'].sum():,} round-2 trails, "
                  f"{(b['error'] != '').sum()} unreadable", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
