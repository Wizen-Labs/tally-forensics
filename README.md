# tally-forensics

**Project** · statistical audit of the Brazilian presidential vote tally from public TSE ballot-box reports
**Version** · v0.5 · **Author** · Eduardo Wizentier ([@Wizen-Labs](https://github.com/Wizen-Labs)) · **Licence** · MIT for code (data excluded, see LICENSE)

The tool downloads TSE's per-section ballot-box reports (*Boletim de Urna*) and verifies them against TSE's SHA-512
files. It rebuilds the presidential tally section by section and applies two filters:

- **Temporal:** did sections that reached TSE at a given time, in particular during the 19:00 to 20:08 BRT publication
  freeze of 2026-10-04, behave differently from comparable sections?
- **Geographic:** do sections disagree with their own polling-location neighbours more in some states or
  municipalities than in others?

It is designed to give a falsifiable answer either way. Read [METHODOLOGY.md](METHODOLOGY.md) before reading any
result.

**Authorship.** The audit's concept is the original idea of Eduardo Wizentier (@Wizen-Labs): analysing vote
deviations through two filters, geographic and transmission time, to look for patterns that normal causes do not
explain. He also made the method decisions and reviewed the work.

**AI assistance.** The data analysis and the code were developed with Claude Opus 5.5 by
[Anthropic](https://www.anthropic.com).

**Data.** All data come from TSE's public open-data and results services.

<!-- phase2:start -->
**Phase 2: live projection.** A live projection of the run-off result was developed in the private lab, announced
in public as "phase B" with hashes only from 2026-10-20, and revealed on 2026-10-28.

**Credit (phase 2).** One component of the live run-off projection, the municipal swing model
(`project.project_swing`), was inspired by Rodrigo Mahlmeister's live projection of the 2026 first round, as reported
by [NeoFeed](https://neofeed.com.br/finde/como-um-pesquisador-brasileiro-criou-um-algoritmo-que-simulou-e-acertou-o-resultado-do-1o-turno/).
No code from his project was used; this implementation is independent.
<!-- phase2:end -->

**Phase B: live run-off projection.** A separate pre-registration, frozen on 2026-10-20, covers a live statistical
projection of the run-off from the first sections counted. Its files stayed private until after the election, with
their SHA-256 hashes and an OpenTimestamps proof published in [`commitments/`](commitments/). They were revealed on
2026-10-28; [`commitments/README.md`](commitments/README.md) explains how to check that nothing was changed. The
election-night result is in [FINDINGS.md](FINDINGS.md) (P12).

## Quick start
```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m tally all --year 2022 --uf RR AC          # small calibration run
.venv\Scripts\python -m tally all --year 2022 --all-ufs           # full calibration (several GB)
.venv\Scripts\python -m tally all --year 2026 --all-ufs           # refused until the protocol is frozen
```

The reports are written to `reports/<year>_t<turn>_<timestamp>/`:

| File | Content |
|---|---|
| `summary.md`, `summary.json` | Headline results |
| `integrity.csv` | Deterministic checks I1 to I7 and the reconciliation |
| `window_tests.csv` | Primary, sensitivity and placebo window tests |
| `arrival_curve.png/.csv` | Sections received over time and the tally in arrival order |
| `heatmap_uf_by_time.png/.csv` | Geography × reception time residuals |
| `by_uf.csv`, `by_municipality.csv` | Geographic summaries |
| `fingerprint.png` | Turnout vs. share (Klimek et al. 2012) |

## Layout
| Path | Content |
|---|---|
| `tally/fetch.py` | Download, SHA-512 verification, append-only manifest |
| `tally/load.py` | Parses the bweb files into one row per section and converts the clocks to BRT |
| `tally/integrity.py` | Deterministic checks |
| `tally/residuals.py` | Within-location leave-one-out residuals |
| `tally/temporal.py` | Arrival curve, residuals by time bin, permutation test |
| `tally/geo.py` | State and municipality summaries, last-digit test |
| `tally/analyze.py` | Pre-registered run and report |
| `tally/live.py` | Live collector of TSE's results site (minute-by-minute, content-addressed archive) |
| `exploratory/` | Exploratory analyses, outside the pre-registration |
| `PREREGISTRATION_ROUND2.md` | Round-2 audit protocol (frozen 2026-10-20, tag `round2-prereg`) |
| `commitments/` | Phase B (live projection): file hashes and timestamp proof, to be checked after the election |
| `entendaMe.md` | Step-by-step explanation in Portuguese |
| `config/` | Sources and analysis parameters (data, not code) |
| `tests/` | Synthetic elections with known truth: power and false-alarm tests |

## Limits
See METHODOLOGY §6. In short, section-level statistics can detect differential anomalies by time or place. They
cannot detect a manipulation applied uniformly inside the ballot box, and a deviation never shows intent.
