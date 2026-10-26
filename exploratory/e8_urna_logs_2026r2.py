"""E8: fetch the per-section ballot-box logs of the 2026 run-off (pleito 3221) for every UF.

The logs feed the H7r2 cross-check (logs vs the round-2 bweb files) and the log-based H6r2 sensitivity run.
UFs with the most extended sections come first. Resumable: run again to continue.

    python exploratory/e8_urna_logs_2026r2.py [uf ...] [--rps 30]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tally.config import ufs
from tally.urna_logs import LogCrawler

FIRST = ["rj", "sp", "ba", "pe", "pb"]

ap = argparse.ArgumentParser()
ap.add_argument("ufs", nargs="*")
ap.add_argument("--rps", type=float, default=30.0)
ap.add_argument("--workers", type=int, default=24)
a = ap.parse_args()
order = [u.lower() for u in a.ufs] or FIRST + [u.lower() for u in ufs() if u.lower() not in FIRST]
crawler = LogCrawler(max_rps=a.rps, workers=a.workers, log=lambda m: print(m, flush=True))
for uf in order:
    try:
        print(crawler.run_uf(uf), flush=True)
    except Exception as e:
        print(f"{uf}: FAILED {type(e).__name__}: {e}", flush=True)
