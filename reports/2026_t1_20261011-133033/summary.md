# Tally forensics report: 2026 round 1

**Tool** · tally v0.2.0 · generated 2026-10-11T13:39:27
**Coverage** · 28 UF files · 499,206 counted sections

## Integrity checks (deterministic)

| Check | Description | Tested | Violations |
|---|---|---:|---:|
| I1 | presidential votes (valid + blank + null + annulled) == turnout | 499,206 | 0 |
| I2 | eligible == turnout + abstentions | 499,206 | 0 |
| I3 | turnout <= eligible | 499,206 | 0 |
| I4 | section key is unique | 499,206 | 0 |
| I5 | a ballot-box serial number is used by only one section (Brazil only; contingency boxes and BU recovery can explain cases, check each) | 497,897 | 0 |
| I6 | clock order: opening < closing <= BU emission <= TSE reception (BRT, Brazil, complete clocks) | 497,895 | 60 |
| I6b | informational: sections with no opening/closing time recorded (e.g. BU recovered by contingency procedure) | 497,897 | 2 |
| I7 | no BU received by TSE before polls close (17:00 BRT, Brazil only) | 497,897 | 0 |
| R-22 | sum of section BUs for #22 == official total | 56,104,503 | 0 |
| R-13 | sum of section BUs for #13 == official total | 53,879,538 | 0 |

## Window tests (within-location permutation)

Primary hypothesis H1 at alpha = 0.01: effect -0.085 pp, p = 0.4043 (no evidence against null)

| Window | Metric | Locations | In | Out | Effect (pp) | p |
|---|---|---:|---:|---:|---:|---:|
| primary: freeze window | margin_resid_adj | 7,687 | 25,828 | 34,863 | -0.085 | 0.4043 |
| primary: freeze window | a_resid_adj | 7,687 | 25,828 | 34,863 | -0.049 | 0.2789 |
| primary: freeze window | turnout_resid_adj | 7,687 | 25,828 | 34,864 | +0.061 | 0.0245 |
| primary: freeze window | margin_resid | 7,687 | 25,828 | 34,864 | -0.449 | 0.0005 |
| sensitivity: start -15 min | margin_resid_adj | 8,875 | 30,961 | 38,270 | -0.045 | 0.8461 |
| sensitivity: start -15 min | a_resid_adj | 8,875 | 30,961 | 38,270 | -0.030 | 0.6877 |
| sensitivity: start -15 min | turnout_resid_adj | 8,875 | 30,961 | 38,271 | -0.003 | 0.9040 |
| sensitivity: start -15 min | margin_resid | 8,875 | 30,961 | 38,271 | -0.498 | 0.0005 |
| sensitivity: start +15 min | margin_resid_adj | 5,367 | 17,400 | 24,157 | -0.131 | 0.0775 |
| sensitivity: start +15 min | a_resid_adj | 5,367 | 17,400 | 24,157 | -0.071 | 0.0540 |
| sensitivity: start +15 min | turnout_resid_adj | 5,367 | 17,400 | 24,158 | +0.042 | 0.2189 |
| sensitivity: start +15 min | margin_resid | 5,367 | 17,400 | 24,157 | -0.336 | 0.0005 |
| sensitivity: end +15 min | margin_resid_adj | 7,758 | 25,657 | 35,011 | -0.087 | 0.6302 |
| sensitivity: end +15 min | a_resid_adj | 7,758 | 25,657 | 35,011 | -0.052 | 0.4283 |
| sensitivity: end +15 min | turnout_resid_adj | 7,758 | 25,657 | 35,012 | +0.000 | 0.9980 |
| sensitivity: end +15 min | margin_resid | 7,758 | 25,657 | 35,012 | -0.505 | 0.0005 |
| placebo 17:52-19:00 | margin_resid_adj | 10,992 | 48,091 | 38,215 | +0.103 | 0.0465 |
| placebo 17:52-19:00 | a_resid_adj | 10,992 | 48,091 | 38,215 | +0.041 | 0.1209 |
| placebo 17:52-19:00 | turnout_resid_adj | 10,993 | 48,092 | 38,218 | -0.056 | 0.0435 |
| placebo 17:52-19:00 | margin_resid | 10,992 | 48,091 | 38,216 | +0.223 | 0.0005 |
| placebo 20:08-21:16 | margin_resid_adj | 2,650 | 6,998 | 12,771 | +0.198 | 0.3268 |
| placebo 20:08-21:16 | a_resid_adj | 2,650 | 6,998 | 12,771 | +0.085 | 0.3648 |
| placebo 20:08-21:16 | turnout_resid_adj | 2,650 | 6,998 | 12,772 | -0.108 | 0.1504 |
| placebo 20:08-21:16 | margin_resid | 2,651 | 7,006 | 12,773 | -0.343 | 0.0020 |

## Figures

- `arrival_curve.png`: sections received per bin and the arrival-order tally.
- `heatmap_uf_by_time.png`: mean within-location residual by UF and reception time.
- `fingerprint.png`: turnout vs share (Klimek fingerprint).
- `primary_test_null.png`: observed effect against the permutation null.

Read METHODOLOGY.md before interpreting any number here. A small p-value is a reason to look, not a finding.
