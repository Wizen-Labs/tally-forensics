# Changelog

## v0.6.0 · 2026-10-20 (round-2 protocol frozen)
- `PREREGISTRATION_ROUND2.md` and `config/round2_forensics.json` are frozen (tag `round2-prereg`; hashes in
  FINDINGS).
- `commitments/`: phase B (the live run-off projection) is announced and committed by hash, with an
  OpenTimestamps proof; `tools/ots_stamp.py`.

## Unreleased
- Round-2 addendum H6r2 (sections with extended voting hours): `PREREGISTRATION_ROUND2_EXTENSION.md` and
  `tally/extension.py`, fixed and timestamped on 2026-10-25 before TSE published the round-2 bweb files
  (`commitments/round2_extension.sha256`).
- Round-2 addendum H7r2 (ballot-box logs vs bweb): `PREREGISTRATION_ROUND2_LOGS.md` and `tally/urna_logs.py`,
  fixed and timestamped on 2026-10-26 before TSE published the round-2 bweb files
  (`commitments/round2_logs.sha256`). `exploratory/e8_urna_logs_2026r2.py` fetches the logs.
- Round-2 addendum H8r2 (signature search in box logs and section transfers):
  `PREREGISTRATION_ROUND2_SIGNATURES.md`, `tally/signatures.py`, `tally/full_logs.py` and
  `tests/test_signatures.py`, fixed and timestamped on 2026-10-26 before TSE published the round-2 bweb files
  (`commitments/round2_signatures.sha256`). If no signature is found, the result is "no signature found so far".
- 2026-10-28: TSE's round-2 bweb released. Frozen round-2 audit run: H1r2–H5r2 (`exploratory/e27_round2_audit.py`),
  H7r2 (`e28_h7r2.py`), H6r2 (`e29_h6r2.py`); FINDINGS F2–F4. Exploratory check of the 17:00–19:00 window
  (`e25_bu_emission.py`, `e26_late_bu_causes.py`, `e26b_close_stages.py`).
- 2026-10-28: phase B revealed. `tools/export_public.py` now exports the phase-2 files; the frozen copies are in
  `commitments/reveal_round2_prereg/`.

<!-- phase2:start -->
## Unreleased (lab)
- 2026-10-25/26, election night: both systems ran. The post went out at 20:38 BRT (48.3%). The final result was
  48.21%, and both systems stayed inside their bands at every cycle (FINDINGS P12). Night logs, local cards and
  the Colab CSV are in `reports/`.
- Projection pre-registration frozen in the lab.
  - Both systems wait for 2% counted and 24 UFs with 1% counted.
  - The Colab system is the backup, with ±0.8 pp (FINDINGS P11).
- `didatico/` is a teaching edition (Portuguese) of the Colab system.
  - All the code is inline in small explained cells, covering polite downloading, hashes, municipal vs. section
    data, the swing model, the bug history and exercises.
  - Verified on round 1: the projection was 51.0115%.
<!-- phase2:end -->

## v0.5.0 · 2026-10-11 (round-2 audit protocol; repository reorganised)
- The round-2 audit protocol is `PREREGISTRATION_ROUND2.md` with `config/round2_forensics.json`.
- The CLI can be extended by optional `tally/cli_*.py` modules and runs without them.
- FINDINGS is reorganised. The round-2 calibration is renumbered C1 → C4.
- Authorship and AI-assistance notes in README.
<!-- phase2:start -->
- Lab: the repository is split into phase 1 (public audit) and phase 2 (projection, lab only).
- Lab only:
  - `tools/export_public.py` builds the public tree from the lab, using a path allowlist and block markers, and
    refuses to export if a phase-2 term leaks;
  - `PREREGISTRATION_ROUND2_PROJECTION.md` with `config/round2_projection.json`;
  - `tally/cli_projection.py`.
<!-- phase2:end -->

## v0.4.0-dev · 2026-10-11 (round-2 pre-registration draft)
- Round-2 audit pre-registration (`PREREGISTRATION_ROUND2.md`).
- `temporal.scan_bins` (round-2 primary test) and `temporal.reception_gaps`.
- `exploratory/c4_round2_calibration_2022.py` (FINDINGS C4).
- The collector's `run` never stops on a failing cycle, and accepts an `on_cycle` callback.
<!-- phase2:start -->
- Phase 2:
  - `tally/live_projection.py` implements the pre-registered projection, and `tally live --project` runs it every
    cycle;
  - `project.round1_groups` is factored out of `merge_rounds`;
  - tests include live path = backtest path.
<!-- phase2:end -->

## v0.3.0-dev · 2026-10-11
- `exploratory/e3_live_publication_2026.py` maps TSE's live files and their timing.
- `tally/live.py` and `tally live --election <code> [--once | --interval 60 --until HH:MM]`: a live collector.
  - It makes conditional requests and stores responses content-addressed and append-only.
  - It keeps its state across restarts and retries failed downloads.
  - `load_state` replays the archive.
- `exploratory/e4_live_collector_check_2026r1.py`.
- The 2022 round-2 source is added to `sources.json`.
<!-- phase2:start -->
- Phase 2: run-off projection in `tally/project.py` and `tally/backtest.py`.
  - The transfer matrix is bounded to [0, 1] and partially pooled UF → region → Brazil.
  - The municipal model has a neutral prior, the `project_swing` model and an `exact` proxy; the `r1_order` proxy
    was refuted.
  - `backtest.run_cross` (FINDINGS P1–P4) and synthetic projection tests.
<!-- phase2:end -->

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
