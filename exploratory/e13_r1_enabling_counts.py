"""E13: round-1 enabling events per log, to find round-1 integrity-test boxes reused in round 2 (H8r2 hunt).

A test box's "voters" are typed by a servant: almost every one is enabled manually ("Solicitação de dado pessoal do
eleitor para habilitação manual", "Dado digitado confere"), with no poll-worker authorisation, and the fingerprint
taken matches one already recorded that day ("Digital coletada bate com uma digital gravada após o registro").
Counts of round-1 (04/10/2026) event types only; no trail, no round-2 line, no personal data.

    .venv/Scripts/python exploratory/e13_r1_enabling_counts.py [--dest D:/tally-forensics-data/urna_logs_full]
"""
import argparse
import json
import re
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tally import DATA_DIR

SRC = DATA_DIR / "urna_logs" / "p3221" / "raw"
OUT = Path(__file__).resolve().parents[1] / "reports" / "h8r2" / "r1_enabling_counts.jsonl"
NAME = re.compile(r"o03221([a-z]{2})(\d{5})(\d{4})(\d{4})-log\.jez\.([0-9a-f]{12})$")
DAY = "04/10/2026"
EVENTS = {"votes": "O voto do eleitor foi computado", "bio": "Tipo de habilita",
          "manual_ask": "Solicitação de dado pessoal do eleitor para habilitação manual",
          "data_ok": "Dado digitado confere", "worker_ok": "habilitou o eleitor",
          "same_finger": "Digital coletada bate com uma digital gravada", "inspection": "Inspeção da urna iniciada"}


def counts(path: str) -> dict:
    m = NAME.search(path)
    with zipfile.ZipFile(path) as z:
        text = z.read(next(n for n in z.namelist() if n.endswith(".dat"))).decode("latin1")
    c = dict.fromkeys(EVENTS, 0)
    boxes = set()
    for line in text.splitlines():
        if not line.startswith(DAY):
            continue
        f = line.split("\t")
        if len(f) < 5:
            continue
        msg = f[4]
        for k, prefix in EVENTS.items():
            if (prefix in msg) if k == "worker_ok" else msg.startswith(prefix):
                if k == "bio" and "biom" not in msg:
                    continue
                c[k] += 1
                break
        boxes.add(f[2])
    return {"uf": m[1], "mun": int(m[2]), "zone": int(m[3]), "sec": int(m[4]), "sha12": m[5], **c,
            "boxes": sorted(boxes)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="D:/tally-forensics-data/urna_logs_full")
    ap.add_argument("--procs", type=int, default=2)
    a = ap.parse_args()
    files = {}
    for d in (SRC, Path(a.dest)):
        for p in d.glob("*/o03221*-log.jez.*"):
            files.setdefault(p.name, str(p))
    print(f"{len(files):,} logs", flush=True)
    with ProcessPoolExecutor(a.procs) as ex, open(OUT, "w", encoding="utf-8") as fh:
        for i, r in enumerate(ex.map(counts, sorted(files.values()), chunksize=200), 1):
            fh.write(json.dumps(r) + "\n")
            if i % 50000 == 0:
                print(f"{i:,}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
