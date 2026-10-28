# Deviation 01 of H8r2: S6' replaces S6 at real vote rates (sealed before any run)

Fixed on 2026-10-27, after E15 showed that the frozen S6 cannot fire (its spike needs 6-10 votes in one box-minute;
a real box casts at most 3). The frozen S6 result stays reported as run. This deviation adds S6'; it does not edit
the frozen files. Code: `tally/s6prime.py`, `tests/test_s6prime.py`, runner `exploratory/e18_s6prime.py`; their
SHA-256 is sealed with this file and timestamped with OpenTimestamps. The runner is executed once; every result is
reported. Requested by the author: the deviation is to be as sensitive as the data allow.

## What is tested
One trigger acting on many boxes in the same clock minute (BRT), seen as either:
- **A:** boxes that cast at least 3 votes in that minute (a "peak"), more than the local rate predicts (Poisson);
- **B1 / B2:** more votes in total, over all boxes, in that 1-minute / 2-minute bin than the local rate predicts
  (normal approximation with overdispersion estimated robustly from all bins). B sees one extra vote in each of
  many boxes; B2 tolerates box clocks that differ by up to a minute.

Expected count of a bin = its exposure (boxes in their interior) x the rate in the bins within +-20 minutes,
leaving out the bin and +-2 minutes, with the window kept symmetric near the ends of the day. A box's interior runs
from 15 minutes after its first vote to 15 minutes before its last. Bins with fewer than 5 baseline minutes on a
side are not tested.

## Data and exclusions
- Per-voter "O voto do eleitor foi computado" times from E12, rounds 1 and 2, halves D and C.
- Same exclusions as E15 (`reports/h8r2/s1_s6/exclusions.csv`): sections with aggregated sections; the 5 SE round-1
  integrity-test sections in round 1. ZZ has no municipal offset and is left out (agreed with the author).
- Box clock + the frozen UF/municipal offset = BRT.

## Flags and decision
- Bonferroni within each statistic x half x round, over the tested bins, alpha 0.01.
- Every flagged bin is reported with its counts; for A, with the boxes that peaked.
- **Unexplained pattern** (reported with the section list for physical check) if a round-2 bin flagged by any
  statistic in D lies within +-2 minutes of a round-2 bin flagged by any statistic in C, **and** no round-1 bin
  (any statistic, either half) is flagged within +-2 minutes of the same time of day. A real trigger acts on both
  halves at once; a time-of-day habit shows up in round 1 too.
- Otherwise, flagged round-2 bins are leads: followed in D under §0; a C-only lead needs its own sealed test.
- Round-1 flags are the control and are reported the same way.

## Checks before sealing (synthetic, `tests/test_s6prime.py`)
- 3,000 independent boxes with an opening queue and a lunch dip: no bin flagged by A, B1 or B2 (5 extra seeds:
  none; smallest p about 1e-3 against a threshold of about 2e-5).
- Detected in 10 of 10 random minutes: 3 votes in the same minute in 10 boxes (A); 1 vote in the same minute in
  200 of 3,000 boxes (B1).
- Real halves have about 200,000 boxes, so B needs more boxes there; the power on real D data is measured after
  the run (injections into D round 2) and reported without changing this rule.
