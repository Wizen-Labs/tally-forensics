# Sealed test C-02: S5 flags in half C, poll-worker turnover or a common pattern (H8r2 §0)

Fixed on 2026-10-27, after the fixed detector S5 ran on both halves (E15) and before any half-C field beyond the
S5 p-values was read. Lead and context: `reports/h8r2/hunt_log.md` (entry "S1–S6 on both halves (E15)"). The test
is run once with `exploratory/e16_c02_s5_turnover.py` (its SHA-256 is sealed with this file); the result is
reported whatever it is.

- **Explanation under test (found on D):** the S5 score is the poll worker's fingerprint matched against the
  registered poll workers, logged only for manual enablings. S5 flags therefore mark boxes where who authorises
  manual enablings changed between rounds, a box-specific change with no common direction.
- **D benchmarks (hunt log):** scored trails manual 100%; flagged boxes with median score up 0.584; mean |change in
  non-match share| 0.299 flagged vs 0.082 unflagged.
- **Data:** half C only; the boxes in `reports/h8r2/s1_s6/s5.parquet` with half = C (S5-tested, paired). From the
  E12 trail tables `<uf>_r1.parquet`, `<uf>_r2.parquet` of the C UFs, only the columns box, n_scores, score_last and
  bio of those boxes. Nothing else of half C.
- **Per box and round** (trails with n_scores > 0): median of score_last; non-match share = share of score_last
  <= 12. Changes are round 2 minus round 1. "Flagged" = S5 flag of E15 (unchanged).
- **Predictions:**
  - P1 (no common direction): among flagged C boxes with a defined median change other than 0, the share with the
    median up is in [0.35, 0.65].
  - P2 (mix change): mean |change in non-match share| of flagged C boxes >= 2 x that of unflagged C boxes.
  - P3 (score = poll worker): in round 2 of the tested C boxes, the share of scored trails with bio = 0 is >= 0.99.
- **Decision:**
  - P1, P2 and P3 hold: **explanation supported**; S5 is closed as poll-worker turnover in both halves, and S5 as
    frozen is reported as not measuring voter trails.
  - P1 fails (one direction above 0.65): a change common to C boxes that the explanation does not predict; the
    flagged C boxes become a lead (an unexplained pattern if no ordinary explanation is found), and the C list is
    reported.
  - P3 fails: the score has another meaning in C; S5 is reopened and reported as such.
  - Otherwise (only P2 fails): inconclusive; reported as such.
