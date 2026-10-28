"""E9: H8r2 second pass. Fetch the full raw log of every round-2 section that the H7r2 crawl summarised but did not keep.

Runs `tally.full_logs.fetch_uf` for each UF (frozen code, at most 30 requests/s). Resumable: run again to continue.

    python exploratory/e9_full_logs_2026r2.py [uf ...] [--dest D:/tally-forensics-data/urna_logs_full] [--rps 30]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tally.config import ufs
from tally.full_logs import fetch_uf

ap = argparse.ArgumentParser()
ap.add_argument("ufs", nargs="*")
ap.add_argument("--dest", default="D:/tally-forensics-data/urna_logs_full")
ap.add_argument("--rps", type=float, default=30.0)
ap.add_argument("--workers", type=int, default=24)
a = ap.parse_args()
dest = Path(a.dest)
dest.mkdir(parents=True, exist_ok=True)
order = [u.lower() for u in a.ufs] or [u.lower() for u in ufs()]
for uf in order:
    try:
        print(fetch_uf(uf, dest, max_rps=a.rps, workers=a.workers, log=lambda m: print(m, flush=True)), flush=True)
    except Exception as e:
        print(f"{uf}: FAILED {type(e).__name__}: {e}", flush=True)
