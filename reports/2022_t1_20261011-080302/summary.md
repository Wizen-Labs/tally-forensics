# Tally forensics report: 2022 round 1

**Tool** · tally v0.2.0 · generated 2026-10-11T08:12:54
**Coverage** · 28 UF files · 472,024 counted sections

## Integrity checks (deterministic)

| Check | Description | Tested | Violations |
|---|---|---:|---:|
| I1 | presidential votes (valid + blank + null + annulled) == turnout | 472,024 | 0 |
| I2 | eligible == turnout + abstentions | 472,024 | 0 |
| I3 | turnout <= eligible | 472,024 | 0 |
| I4 | section key is unique | 472,024 | 0 |
| I5 | a ballot-box serial number is used by only one section (Brazil only; contingency boxes and BU recovery can explain cases, check each) | 471,010 | 14 |
| I6 | clock order: opening < closing <= BU emission <= TSE reception (BRT, Brazil, complete clocks) | 470,993 | 0 |
| I6b | informational: sections with no opening/closing time recorded (e.g. BU recovered by contingency procedure) | 471,010 | 17 |
| I7 | no BU received by TSE before polls close (17:00 BRT, Brazil only) | 471,010 | 0 |

## Window tests (within-location permutation)

Primary hypothesis H1 at alpha = 0.01: effect -0.056 pp, p = 0.4318 (no evidence against null)

| Window | Metric | Locations | In | Out | Effect (pp) | p |
|---|---|---:|---:|---:|---:|---:|
| primary: freeze window | margin_resid_adj | 9,550 | 37,551 | 36,430 | -0.056 | 0.4318 |
| primary: freeze window | a_resid_adj | 9,550 | 37,551 | 36,430 | -0.024 | 0.5472 |
| primary: freeze window | turnout_resid_adj | 9,550 | 37,551 | 36,430 | -0.017 | 0.6382 |
| primary: freeze window | margin_resid | 9,553 | 37,576 | 36,434 | -0.008 | 0.8756 |
| sensitivity: start -15 min | margin_resid_adj | 9,495 | 39,628 | 33,845 | -0.068 | 0.3913 |
| sensitivity: start -15 min | a_resid_adj | 9,495 | 39,628 | 33,845 | -0.036 | 0.4068 |
| sensitivity: start -15 min | turnout_resid_adj | 9,495 | 39,628 | 33,845 | -0.010 | 0.8596 |
| sensitivity: start -15 min | margin_resid | 9,498 | 39,653 | 33,849 | +0.007 | 0.9010 |
| sensitivity: start +15 min | margin_resid_adj | 9,703 | 35,993 | 40,180 | +0.004 | 0.9390 |
| sensitivity: start +15 min | a_resid_adj | 9,703 | 35,993 | 40,180 | -0.004 | 0.8881 |
| sensitivity: start +15 min | turnout_resid_adj | 9,703 | 35,993 | 40,180 | -0.010 | 0.7351 |
| sensitivity: start +15 min | margin_resid | 9,705 | 36,010 | 40,184 | +0.018 | 0.7281 |
| sensitivity: end +15 min | margin_resid_adj | 8,868 | 34,678 | 33,563 | -0.119 | 0.1004 |
| sensitivity: end +15 min | a_resid_adj | 8,868 | 34,678 | 33,563 | -0.057 | 0.1654 |
| sensitivity: end +15 min | turnout_resid_adj | 8,868 | 34,678 | 33,563 | -0.001 | 0.9900 |
| sensitivity: end +15 min | margin_resid | 8,874 | 34,718 | 33,570 | -0.093 | 0.0710 |
| placebo 17:52-19:00 | margin_resid_adj | 7,216 | 30,744 | 25,097 | +0.008 | 0.9120 |
| placebo 17:52-19:00 | a_resid_adj | 7,216 | 30,744 | 25,097 | +0.001 | 0.9795 |
| placebo 17:52-19:00 | turnout_resid_adj | 7,216 | 30,744 | 25,097 | -0.025 | 0.3903 |
| placebo 17:52-19:00 | margin_resid | 7,217 | 30,749 | 25,098 | +0.140 | 0.0245 |
| placebo 20:08-21:16 | margin_resid_adj | 4,843 | 14,650 | 23,237 | -0.037 | 0.6962 |
| placebo 20:08-21:16 | a_resid_adj | 4,843 | 14,650 | 23,237 | -0.017 | 0.7051 |
| placebo 20:08-21:16 | turnout_resid_adj | 4,843 | 14,650 | 23,237 | +0.006 | 0.9260 |
| placebo 20:08-21:16 | margin_resid | 4,849 | 14,671 | 23,256 | -0.244 | 0.0010 |

## Figures

- `arrival_curve.png`: sections received per bin and the arrival-order tally.
- `heatmap_uf_by_time.png`: mean within-location residual by UF and reception time.
- `fingerprint.png`: turnout vs share (Klimek fingerprint).
- `primary_test_null.png`: observed effect against the permutation null.

Read METHODOLOGY.md before interpreting any number here. A small p-value is a reason to look, not a finding.
