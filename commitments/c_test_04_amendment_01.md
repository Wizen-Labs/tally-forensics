# C-04 amendment 01: use the BUs whose hash status is "Recebido" too

Fixed on 2026-10-28, after C-04 was sealed (commit 07d1665) and before it was run; no round-2 vote count of half C
had been read. Logged deviation.

## Why
The author asked why TSE lists 517,287 sections when there are 499,176 boxes. Counting the H7r2 crawl index
(structural fields only, no votes):
- 517,287 sections listed (514,572 in Brazil, 2,715 abroad);
- 18,039 have no files of their own (aggregated into another section's box; their votes are in that box's BU), and
  41 were not installed, 30 + 1 listed without a log;
- 499,176 sections have a box with files: 482,654 with status "Totalizado" and 16,522 with "Recebido" when the
  crawl ran (26/10). This matches the 499,176 boxes.
C-04 as sealed keeps only "Totalizado", which would drop the 16,522 "Recebido" boxes (3.3%) from the test. A
collapse or zero could sit exactly there.

## Change
`exploratory/e23_c04_collapse_a1.py` replaces `e23_c04_collapse.py`: identical except that a BU whose hash status
is "Totalizado" or "Recebido" is used, the status is kept per section (`hash_status`), and the counts per status
are reported. Every other rule of C-04 is unchanged. Flagged sections are listed with their status.
