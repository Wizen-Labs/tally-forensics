# Pre-registration: forensic audit of the 2026 presidential run-off (25 October 2026)

**Project** · tally-forensics · round-2 audit protocol
**Status** · **FROZEN** on 2026-10-20, before round 2 (git tag `round2-prereg`; hashes in FINDINGS.md)
**Parameters** · `config/round2_forensics.json`. The code paths are listed in §4.
**Rule** · The author freezes this document with a git tag (`round2-prereg`), and the SHA-256 hashes are recorded in
FINDINGS.md. Any later change is a logged deviation. Every result is reported, including those that look bad.

The audit runs after TSE publishes the round-2 ballot-box files, usually the day after the election. On election
night the live collector archives TSE's publication minute by minute, which gives the publication timeline used in
H2r2 and H5r2.

---

## 1. Data
- The round-2 bweb files, verified against TSE's SHA-512.
- The collector archive from election night (`python -m tally live --election 6258 --interval 30`, from about 16:55
  BRT). It reads:
  - the national file and the 28 UF files (presidential results);
  - the 28 progress files (sections counted per municipality);
  - the 28 section-configuration files;
  - the municipal result files whose progress changed.

  Every response is stored content-addressed, and every request is logged (FINDINGS E4).
- **Methods:** as in `METHODOLOGY.md` §2–§4.2, i.e. the within-location residual and the covariate-adjusted
  permutation test, which were calibrated on 2022 and frozen for round 1.

## 2. Hypotheses

| ID | Null hypothesis | Test | Decision |
|---|---|---|---|
| **H1r2 (primary)** | In every 10-minute reception bin, from the first reception until 99% of sections are received, sections in the bin have the same adjusted margin residual as their own polling-location siblings received outside it | `temporal.scan_bins`, 2,000 permutations, seed 20261025 | Reject a bin if p < 0.01 / number of bins (Bonferroni) |
| H2r2 | The same, for each **publication freeze** found in the archive | `temporal.window_test`, adjusted. Sensitivity: start ±15 min | Reject if p < 0.01 / number of freezes |
| H3r2 | No nationwide reception gap of 5 minutes or more before 95% of sections are received | `temporal.reception_gaps` | Any gap is reported as a process anomaly, with start, end and duration |
| H4r2 | Integrity checks I1–I7 have zero violations; the sum of the BUs equals the official totals exactly | `integrity.run` | Factual |
| H5r2 | Final live municipal results (collector archive) equal the sum of the BUs of each municipality | as in FINDINGS E4 | Factual; any difference is listed by municipality |

**A publication freeze is defined as** a period of at least 10 minutes in which the national result file in the
collector archive did not change, while at least 1% of sections were received by TSE (`DT_BU_RECEBIDO`) during that
period. This makes "freeze" objective: in round 1 it could only be taken from press reports.

## 3. Decision rule and wording
- A Bonferroni rejection in H1r2 or H2r2 is reported as **"a pattern that needs an explanation"**. It is never
  reported as fraud. Before any interpretation, the known innocent causes must be checked: queues, section rank,
  aggregated sections and contingency boxes (METHODOLOGY §5).
- H3r2 and H5r2 are reported factually, with timestamps.
- **What the audit cannot see:** a uniform manipulation inside the ballot box (METHODOLOGY §6).

## 3a. Calibration on the 2022 run-off (done before freezing; FINDINGS C4)
- **H3:** no reception gap of 5 minutes or more before 95% of sections were received.
- **H1 bin scan:** 18 bins (17:00–19:50); 0 rejections at the Bonferroni threshold (0.00056), and 0 even at the
  nominal 0.01. The smallest p is 0.011.
- The test therefore behaves as a valid test on a run-off with no known incident. Report:
  `reports/calibration_round2_2022/`.

---

## 4. Code and files covered by the freeze
`PREREGISTRATION_ROUND2.md`, `config/round2_forensics.json`, `tally/temporal.py`, `tally/residuals.py`,
`tally/integrity.py`, `tally/live.py`.

<!-- phase2:start -->
## 5. Phase 2: live projection (sealed until after the election)
A second, separate pre-registration covers a live projection of the run-off result from the first sections
counted. It is kept private until after the election.
- **Its SHA-256 will be published here at the freeze** (by 2026-10-24), before the election.
- **After the election** the document and its code will be made public, so anyone can check that they match this
  hash (commit–reveal).
<!-- phase2:end -->
