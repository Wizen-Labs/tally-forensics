# E8: round-1 validation of the round-2 box logs (H7r2 §4), all UFs

Run 2026-10-27 after the H7r2 crawl finished (04:31Z), before any round-2 bweb exists.
Script: `exploratory/e8b_round1_validation_2026.py`. Tables: `round1_validation_by_uf.csv`, `_cases.csv`, `_unmatched.csv`.

## Crawl
- 517,179 sections in TSE's round-2 list: 499,176 with log, 17,931 aux HTTP 404, 72 "no log listed".
- Every aux 404 outside ZZ is a section listed as aggregated in the round-1 bweb (17,931 of 17,931 checked).
  The 42 other unmatched sections are all abroad (ZZ) with no log.
- Every round-1 bweb section has a log folder (bweb_only = 0).

## Same box in both rounds (494,371 sections with round-1 events)
| Result | Sections |
|---|---|
| votes, close (±60 s) and box all match | 492,350 |
| explained: box replaced (ready > 5 min late, fewer votes) | 2,004 |
| unexplained | 17 |

4,805 sections changed box between rounds (no round-1 events in the round-2 log).

## The 17 unexplained cases (leads; raw logs come with the second pass)
- **9 sections, close event missing:** votes and box match, but the round-1 log has no
  "Procedimento de encerramento confirmado" (AL 1, BA 2, MS 1, PA 4, SC 1). Several bweb closes are late (17:31–22:52).
- **4 sections in Sergipe, box differs:** the log's box is not the round-1 effective box, and that box is in no
  round-1 bweb row. Votes differ by −5, −3, +6, −60; closes by 49 s to 18 min.
  (SE 31690/12/87, 31712/13/82, 31755/5/143, 32514/35/57.)
- **4 sections, log one vote short** with the same box, an on-time start and a matching close
  (ES 56995/53/211, SP 63614/227/305, 64254/291/346, 71072/260/37).

To check on the raw logs: the event lines around the close, the box serials and any recovery or contingency events.
