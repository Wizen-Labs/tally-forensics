# Protocol addendum H6r2: sections with extended voting hours (25 October 2026)

**Project** · tally-forensics · round-2 audit, addendum
**Status** · Fixed on 2026-10-25, during the count and **before TSE published the round-2 ballot-box (bweb) files**.
The SHA-256 of this file and of `tally/extension.py` is timestamped with OpenTimestamps (`commitments/`).
**Rule** · Any later change is a logged deviation. Every result is reported, including those that look bad.

## 0. What this is, and what it is not
- On election day TSE extended voting until 19:00 BRT in some places. Some ballot boxes closed at the normal time and
  others later. This addendum asks whether the extended sections differ from comparable sections, for transparency.
- **It is not a pre-registration in the sense of the 20 October freeze.** It was written after the polls closed,
  when partial **municipal** results had been seen (about half of sections counted). It was fixed before any
  **section-level** data were available, and the tests below run only on section-level data.
- The motivation is transparency about an unusual event. A rejected null hypothesis is a statistical deviation to be
  explained (for example, people who vote late differ from early voters, or the reason for the extension affects
  who votes); it is **never** described as fraud.
- The frozen round-2 protocol (`PREREGISTRATION_ROUND2.md`, tag `round2-prereg`) is unchanged and runs first.

## 1. Data
- Round-2 bweb files (2026, election 6258), verified against TSE's SHA-512, and round-1 bweb files (2026, already
  in `data/manifest.jsonl`).
- Sections are matched across rounds by (UF, municipality, zone, section). Sections with fewer than 30 votes for the
  two candidates in either round are excluded. Abroad (ZZ) is excluded.
- Calibration: the 2022 round-1 and round-2 bweb files.

## 2. Definitions
- **Extended section:** closing time (`DT_ENCERRAMENTO`, converted to BRT by the frozen pipeline) at or after
  **17:30 BRT**. In the 2022 run-off only 0.07% of sections closed after 17:30, so in a run-off a later close is
  almost always the extension, not a queue.
  - Sensitivity, reported alongside: cutoff 18:00 BRT; the raw local clock instead of BRT; and TSE's official list
    of extended locations, if TSE publishes one.
- **Changes per section (round 2 minus round 1, same section):**
  - `d_share`: change in A/(A+B), with A = 22 (Flávio Bolsonaro) and B = 13 (Lula); **primary**;
  - `d_turnout`: change in turnout (attendance / eligible);
  - `d_blank_null`: change in (blank + null) / attendance.

## 3. Hypotheses (all two-sided)

| ID | Null hypothesis | Test (`tally/extension.py`) |
|---|---|---|
| **H6a** | Within a municipality, extended sections change like the on-time sections of the same municipality | `within_municipality`: labels permuted within municipality; 10,000 permutations, seed 20261025 |
| **H6b** | Municipalities with at least 50% of sections extended change like municipalities with at most 20% extended, in the same UF and round-1 share decile | `across_municipalities`: labels permuted within UF × decile strata; 10,000 permutations, seed 20261025 |
| **H6c** | Extended sections are no more often turnout outliers than expected: change beyond the 0.1% / 99.9% band of on-time sections of the same UF (expected rate 0.2%) | `turnout_outliers`, exact binomial test |

H6a and H6b run on each of the three metrics, which gives 7 tests in all.

- **Decision:** reject a null if p < 0.01 / 7 (Bonferroni). `d_share` in H6a is the headline result.
- **Effect size:** every test reports its statistic in percentage points, whatever the p-value. Below 0.5 pp on
  `d_share`, a significant result is called "statistically detectable but small".
- **H6c lists every flagged section** (UF, municipality, zone, section, turnout in each round), whatever the p-value,
  so that anyone can check them against the printed ballot-box reports.

## 4. Calibration (to run before the 2026 data, reported in FINDINGS)
The same code runs on 2022 round 1 → round 2:
1. **Real late closers of 2022 r2** (closing at or after 17:30), as a natural placebo: no extension happened.
2. **Placebo labels:** 200 random draws of 3% of municipalities as "extended", for H6b; inside those municipalities,
   a random half of sections, for H6a.

The false-alarm rate at p < 0.01 must be at most 3% (expected 1%). If a test exceeds that, it is reported in 2026
as **descriptive only**, with the calibration result beside it. This rule is fixed now and is not tuned afterwards.

## 5. Order of work
1. The frozen round-2 audit (H1r2–H5r2).
2. The calibration in §4, on 2022.
3. H6a–H6c on 2026, then the sensitivity runs in §2.
4. Results go to FINDINGS.md (entry H6r2), clean or not, with the same prominence.
