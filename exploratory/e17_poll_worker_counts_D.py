"""E17 (H8r2 hunt, half D only): poll-worker event counts per round, to explain the S5 flags.

For the S5-tested boxes of half D, counts per day (04/10 and 25/10/2026) of: "Mesário … registrado" (registered),
"Solicita digital do mesário" (authorisation requests), "Biometria coletada não é do mesário" (non-matches),
"habilitou o eleitor" (authorisations). Counts only; no numbers are read or stored.

    .venv/Scripts/python exploratory/e17_poll_worker_counts_D.py [--procs 6]
"""
import argparse
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tally import DATA_DIR
from tally import signatures as sg

ROOT = Path(__file__).resolve().parents[1]
TRAILS = Path("D:/tally-forensics-data/trails")
OUT = ROOT / "reports" / "h8r2" / "poll_worker_counts_D.parquet"
DIRS = (str(DATA_DIR / "urna_logs" / "p3221" / "raw"), "D:/tally-forensics-data/urna_logs_full")
REG = re.compile(r"^Mes\S+ \d+ registrado")
EV = {"ask": "Solicita digital do mes", "nonmatch": "Biometria coletada n", "auth": "habilitou o eleitor"}


def counts(r: tuple) -> dict:
    uf, mun, zone, sec, sha12, box = r
    name = f"{uf}/o03221{uf}{mun:05d}{zone:04d}{sec:04d}-log.jez.{sha12}"
    path = next(f"{d}/{name}" for d in DIRS if os.path.exists(f"{d}/{name}"))
    text = sg.read_log(Path(path).read_bytes())
    out = {"box": box}
    for rnd, day in sg.DAYS.items():
        c = dict.fromkeys(["registered", *EV], 0)
        for line in text.splitlines():
            if not line.startswith(day):
                continue
            f = line.split("\t")
            if len(f) < 5:
                continue
            msg = f[4]
            if REG.match(msg):
                c["registered"] += 1
            elif msg.startswith(EV["ask"]):
                c["ask"] += 1
            elif msg.startswith(EV["nonmatch"]) and "mes" in msg:
                c["nonmatch"] += 1
            elif EV["auth"] in msg:
                c["auth"] += 1
        out.update({f"{k}_r{rnd}": v for k, v in c.items()})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=6)
    a = ap.parse_args()
    s5 = pd.read_parquet(ROOT / "reports" / "h8r2" / "s1_s6" / "s5.parquet")
    s5 = s5[s5["half"] == "D"]
    b = pd.concat([pd.read_parquet(p) for p in sorted(TRAILS.glob("*_boxes.parquet"))])
    b = b[b["box"].isin(s5.index)]
    rows = list(b[["uf", "mun", "zone", "sec", "sha12", "box"]].itertuples(index=False, name=None))
    with ProcessPoolExecutor(a.procs) as ex:
        res = pd.DataFrame(list(ex.map(counts, rows, chunksize=200)))
    res.to_parquet(OUT)
    print(f"{len(res):,} boxes", flush=True)


if __name__ == "__main__":
    main()
