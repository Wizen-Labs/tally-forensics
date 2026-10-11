# Tally forensics report: 2022 round 1

**Tool** · tally v0.1.0 · generated 2026-10-11T07:08:37
**Coverage** · 2 UF files · 3,392 counted sections · **partial: not all UFs present, no national claims**

## Integrity checks (deterministic)

| Check | Description | Tested | Violations |
|---|---|---:|---:|
| I1 | presidential votes (valid + blank + null + annulled) == turnout | 3,392 | 0 |
| I2 | eligible == turnout + abstentions | 3,392 | 0 |
| I3 | turnout <= eligible | 3,392 | 0 |
| I4 | section key is unique | 3,392 | 0 |
| I5 | a ballot-box serial number is used by only one section | 3,392 | 0 |
| I6 | clock order: opening < closing <= BU emission <= TSE reception (BRT, Brazil only) | 3,392 | 0 |
| I7 | no BU received by TSE before polls close (17:00 BRT, Brazil only) | 3,392 | 0 |

## Window tests (within-location permutation)

Primary hypothesis H1 at alpha = 0.01: effect -0.763 pp, p = 0.3128 (no evidence against null)

| Window | Metric | Locations | In | Out | Effect (pp) | p |
|---|---|---:|---:|---:|---:|---:|
| primary: freeze window | margin_resid | 101 | 220 | 278 | -0.763 | 0.3128 |
| primary: freeze window | a_resid | 101 | 220 | 278 | -0.440 | 0.2779 |
| primary: freeze window | turnout_resid | 101 | 220 | 278 | +0.148 | 0.7056 |
| sensitivity: start -15 min | margin_resid | 130 | 307 | 341 | -0.236 | 0.7206 |
| sensitivity: start -15 min | a_resid | 130 | 307 | 341 | -0.087 | 0.8066 |
| sensitivity: start -15 min | turnout_resid | 130 | 307 | 341 | +0.345 | 0.3118 |
| sensitivity: start +15 min | margin_resid | 114 | 251 | 320 | +0.122 | 0.8516 |
| sensitivity: start +15 min | a_resid | 114 | 251 | 320 | +0.091 | 0.8066 |
| sensitivity: start +15 min | turnout_resid | 114 | 251 | 320 | +0.034 | 0.9270 |
| sensitivity: end +15 min | margin_resid | 92 | 193 | 264 | -0.737 | 0.3553 |
| sensitivity: end +15 min | a_resid | 92 | 193 | 264 | -0.404 | 0.3553 |
| sensitivity: end +15 min | turnout_resid | 92 | 193 | 264 | +0.136 | 0.7276 |
| placebo 17:52-19:00 | margin_resid | 99 | 280 | 198 | +0.554 | 0.5392 |
| placebo 17:52-19:00 | a_resid | 99 | 280 | 198 | +0.348 | 0.4638 |
| placebo 17:52-19:00 | turnout_resid | 99 | 280 | 198 | -0.058 | 0.8651 |
| placebo 20:08-21:16 | margin_resid | 22 | 39 | 79 | +0.145 | 0.9330 |
| placebo 20:08-21:16 | a_resid | 22 | 39 | 79 | +0.056 | 0.9560 |
| placebo 20:08-21:16 | turnout_resid | 22 | 39 | 79 | -0.248 | 0.7511 |

## Figures

- `arrival_curve.png`: sections received per bin and the arrival-order tally.
- `heatmap_uf_by_time.png`: mean within-location residual by UF and reception time.
- `fingerprint.png`: turnout vs share (Klimek fingerprint).
- `primary_test_null.png`: observed effect against the permutation null.

Read METHODOLOGY.md before interpreting any number here. A small p-value is a reason to look, not a finding.
