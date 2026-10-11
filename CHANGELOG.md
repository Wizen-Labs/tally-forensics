# Changelog

## v0.5.0 · 2026-10-11 (round-2 audit protocol; repository reorganised)
- The round-2 audit protocol is `PREREGISTRATION_ROUND2.md` with `config/round2_forensics.json`.
- The CLI can be extended by optional `tally/cli_*.py` modules and runs without them.
- FINDINGS is reorganised. The round-2 calibration is renumbered C1 → C4.
- Authorship and AI-assistance notes in README.

## v0.4.0-dev · 2026-10-11 (round-2 pre-registration draft)
- Round-2 audit pre-registration (`PREREGISTRATION_ROUND2.md`).
- `temporal.scan_bins` (round-2 primary test) and `temporal.reception_gaps`.
- `exploratory/c4_round2_calibration_2022.py` (FINDINGS C4).
- The collector's `run` never stops on a failing cycle, and accepts an `on_cycle` callback.

## v0.3.0-dev · 2026-10-11
- `exploratory/e3_live_publication_2026.py` maps TSE's live files and their timing.
- `tally/live.py` and `tally live --election <code> [--once | --interval 60 --until HH:MM]`: a live collector.
  - It makes conditional requests and stores responses content-addressed and append-only.
  - It keeps its state across restarts and retries failed downloads.
  - `load_state` replays the archive.
- `exploratory/e4_live_collector_check_2026r1.py`.
- The 2022 round-2 source is added to `sources.json`.

## v0.2.1 · 2026-10-11 (after the freeze; no change to the analysis)
- `config.py` reads JSON as `utf-8-sig`. The frozen `analysis.json` carries a BOM written by PowerShell, and its hash
  is unchanged.
- Added `exploratory/e1_reception_gap_2026.py`. It is exploratory and not part of the frozen protocol.
- First confirmatory run on 2026 round 1 (FINDINGS F1).

## v0.2.0 · 2026-10-11 (calibration-driven, before the protocol freeze)
- **Primary test is now covariate-adjusted** (METHODOLOGY §4.2). It adjusts for:
  - close-delay bucket;
  - section-rank quintile;
  - log of eligible voters;
  - the aggregated flag.

  The adjustment is fitted on out-of-window sections only. The reason: in the 2022 calibration, the unadjusted test
  rejected a placebo window (FINDINGS C2).
- The unadjusted test is still reported (H2u).
- I5 is restricted to Brazil. I6 is split into I6 (complete clocks) and I6b (missing clocks, informational).
- Fixed a crash on municipalities with no opening times (`ZZ`).
- Added a per-file parse cache keyed by `PARSER_VERSION`.
- Plots are limited to election evening. The data and the tests keep every section.
- Tests: 19 (incl. a heatmap regression test). New ones cover the queue-confounder false alarm, its absorption by the adjustment, and power under the
  confounder.

## v0.1.0 · 2026-10-11
- TSE bweb fetcher with SHA-512 verification and an append-only manifest. Raw files are write-once.
- The parser:
  - handles the 2022 and 2026 schemas (`DS_AGREGADAS` was renamed `DS_SECOES_AGREGADAS`, and the date formats
    differ);
  - infers each municipality's clock offset from the modal opening hour.
- Deterministic integrity checks I1 to I7 and reconciliation against the official totals.
- Within-location leave-one-out residuals for candidate share, margin and turnout.
- Window permutation test stratified by polling location, with primary, sensitivity and placebo windows.
- Geographic summaries, a UF × time heatmap, a Klimek fingerprint and a last-digit test (exploratory).
- Pre-registration draft (METHODOLOGY.md). Analysing 2026 is refused until `protocol_frozen` is set.
- 14 tests, including synthetic power (a 5% injected shift is detected) and false-alarm checks.
