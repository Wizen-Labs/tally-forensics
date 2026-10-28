# Tally forensics report: 2022 round 1

**Tool** · tally v0.1.0 · generated 2026-10-11T07:53:02
**Coverage** · 28 UF files · 472,024 counted sections

## Integrity checks (deterministic)

| Check | Description | Tested | Violations |
|---|---|---:|---:|
| I1 | presidential votes (valid + blank + null + annulled) == turnout | 472,024 | 0 |
| I2 | eligible == turnout + abstentions | 472,024 | 0 |
| I3 | turnout <= eligible | 472,024 | 0 |
| I4 | section key is unique | 472,024 | 0 |
| I5 | a ballot-box serial number is used by only one section | 472,024 | 113 |
| I6 | clock order: opening < closing <= BU emission <= TSE reception (BRT, Brazil only) | 471,010 | 17 |
| I7 | no BU received by TSE before polls close (17:00 BRT, Brazil only) | 471,010 | 0 |

## Window tests (within-location permutation)

Primary hypothesis H1 at alpha = 0.01: effect -0.008 pp, p = 0.8756 (no evidence against null)

| Window | Metric | Locations | In | Out | Effect (pp) | p |
|---|---|---:|---:|---:|---:|---:|
| primary: freeze window | margin_resid | 9,553 | 37,576 | 36,434 | -0.008 | 0.8756 |
| primary: freeze window | a_resid | 9,553 | 37,576 | 36,434 | +0.002 | 0.9470 |
| primary: freeze window | turnout_resid | 9,553 | 37,576 | 36,434 | +0.042 | 0.1000 |
| sensitivity: start -15 min | margin_resid | 9,498 | 39,653 | 33,849 | +0.007 | 0.9010 |
| sensitivity: start -15 min | a_resid | 9,498 | 39,653 | 33,849 | +0.002 | 0.9280 |
| sensitivity: start -15 min | turnout_resid | 9,498 | 39,653 | 33,849 | +0.042 | 0.1019 |
| sensitivity: start +15 min | margin_resid | 9,705 | 36,010 | 40,184 | +0.018 | 0.7281 |
| sensitivity: start +15 min | a_resid | 9,705 | 36,010 | 40,184 | +0.005 | 0.8351 |
| sensitivity: start +15 min | turnout_resid | 9,705 | 36,010 | 40,184 | +0.040 | 0.1184 |
| sensitivity: end +15 min | margin_resid | 8,874 | 34,718 | 33,570 | -0.093 | 0.0710 |
| sensitivity: end +15 min | a_resid | 8,874 | 34,718 | 33,570 | -0.039 | 0.1449 |
| sensitivity: end +15 min | turnout_resid | 8,874 | 34,718 | 33,570 | +0.068 | 0.0085 |
| placebo 17:52-19:00 | margin_resid | 7,217 | 30,749 | 25,098 | +0.140 | 0.0245 |
| placebo 17:52-19:00 | a_resid | 7,217 | 30,749 | 25,098 | +0.061 | 0.0545 |
| placebo 17:52-19:00 | turnout_resid | 7,217 | 30,749 | 25,098 | -0.056 | 0.0710 |
| placebo 20:08-21:16 | margin_resid | 4,849 | 14,671 | 23,256 | -0.244 | 0.0010 |
| placebo 20:08-21:16 | a_resid | 4,849 | 14,671 | 23,256 | -0.111 | 0.0025 |
| placebo 20:08-21:16 | turnout_resid | 4,849 | 14,671 | 23,256 | +0.018 | 0.6502 |

## Figures

- `arrival_curve.png`: sections received per bin and the arrival-order tally.
- `heatmap_uf_by_time.png`: mean within-location residual by UF and reception time.
- `fingerprint.png`: turnout vs share (Klimek fingerprint).
- `primary_test_null.png`: observed effect against the permutation null.

Read METHODOLOGY.md before interpreting any number here. A small p-value is a reason to look, not a finding.
