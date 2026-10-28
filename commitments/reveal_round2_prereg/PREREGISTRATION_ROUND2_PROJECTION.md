# Pre-registration: live projection of the 2026 presidential run-off (25 October 2026)

**Project** · tally-forensics · PHASE 2 (private until after the election; commit–reveal)
**Status** · **FROZEN** on 2026-10-20, before round 2 (git tag `round2-prereg` in the lab; hashes in FINDINGS)
**Parameters** · `config/round2_projection.json`. The code paths are listed in §6.
**Rule** · At the freeze, the SHA-256 of this file is published in the public repository's `PREREGISTRATION_ROUND2.md`
§5. Any later change is a logged deviation. Every number produced on election night is reported, including those
that look bad.

---

## 1. Data
- **Live inputs:** TSE's results site (`resultados.tse.jus.br/oficial/ele2026/6258/…`), read by the collector
  (`python -m tally live --election 6258 --interval 30 --project`) from about 16:55 BRT. It reads:
  - the national file and the 28 UF files (presidential results);
  - the 28 progress files (sections counted per municipality);
  - the 28 section-configuration files;
  - the municipal result files whose progress changed.
- **Archive:** every response is stored content-addressed, and every request is logged (FINDINGS E4).
- **Base:** the 2026 round-1 ballot-box files (499,206 sections), grouped per municipality as A1 (Flávio), B1 (Lula),
  others, blank+null and abstention.

## 2. Model (fixed; no parameter is tuned)
Within each municipality, the counted part's round-1 composition is taken as the municipal round-1 composition times
the share of the electorate counted (the proportional proxy). TSE does not publish live which sections are counted
(FINDINGS E3).

The estimate of Flávio's share of Flávio + Lula votes is the **mean** of two models:
1. **Transfer model without prior:** a bounded transfer matrix from the five round-1 groups to each candidate,
   partially pooled UF → region → Brazil, with a shrunk municipal correction (`project.project_aggregates`, default
   `Params`).
2. **Municipal swing model:** swing and turnout ratio per municipality, shrunk towards UF → region → Brazil
   (`project.project_swing`, defaults `k_mun = 3000`, `k_uf = 20000`).

The tuned configuration of FINDINGS P2 (strong prior plus a completeness threshold) is **excluded**: it failed out of
sample (P3).

## 3. Interval and publication rule
- **Publication gate (both systems):** no projection is shown before **2.0%** of sections are counted (national
  file) **and** at least **24 of the 27 UFs** have 1% of their electorate counted. This is the owner's
  representativeness rule; abroad is modelled but does not count as a UF.
  - In the backtests the gate opened at about 10% counted (17:33 BRT in the 2022 run-off; FINDINGS P11).
  - The checkpoints in §4 that fall before the gate are still computed and logged, but not published.
- **Interval:** estimate ± **0.7 pp**. Source: the largest absolute error of this two-model mean over checkpoints
  2%, 3%, 5%, 10%, 20% and 50% in the two available backtests (2022 r1→r2 and 2022 r1→2026 r1) was 0.625 pp,
  rounded up (FINDINGS P5).

  This is an envelope of 12 observed errors, **not** a probability guarantee. The errors are not monotone in the
  share counted, so the same half-width is used throughout.
- **A winner is "called"** only when the whole interval is on one side of 50%. That means a projected share outside
  49.3%–50.7%, i.e. a projected margin larger than 1.4 pp.
- Each cycle's output is appended to `projections.jsonl` in the archive: time, % counted, raw count, both models, the
  estimate, the interval and the call.

## 4. Evaluation (after the official result)
- **Report:** the error of the estimate at the first cycle after 2%, 3%, 5%, 10%, 20% and 50% counted, against the
  official final share.
- **Success criterion:** |error| ≤ 0.7 pp at every one of these checkpoints. A call, if made, must be correct.
- **On failure:** the failure is reported as such, with its likely cause. The model is not adjusted after the fact.

## 5. Known limits
- Municipal-level live data cap the accuracy at about ±0.5 pp (FINDINGS P4). Section-level accuracy (about 0.1 pp)
  would need section votes, which TSE publishes only hours later.
- Round-2 transfers of the 2026 minor candidates (Cury, Renan Santos, Caiado, Zema and others, 7.8%) are not
  observed in any backtest.
- A publication freeze like round 1's would delay the projection, not bias it.

## 6. Code and files covered by the freeze
`PREREGISTRATION_ROUND2_PROJECTION.md`, `config/round2_projection.json`, `tally/project.py`,
`tally/live_projection.py`, `tally/live.py`, `colab/tally_colab.py`, `colab/make_notebook.py`.

## 7. Backup system (independent Colab notebook)
A second system runs at the same time in Google Colab (`colab/tally_colab.py`, notebook
`colab/tally_live_independent.ipynb`; the teaching edition `didatico/aprenda_apuracao_ao_vivo.ipynb` has the same
logic). It is independent of the main system: its base is TSE's round-1 municipal result files, its code was written
separately, and it runs on another machine and network.
- **Model:** the municipal swing only, shrunk municipality → UF → Brazil, with `k_mun = 2000` and `k_uf = 10000`
  (defaults of `tally_colab.project`, untuned).
- **Gate:** as in §3 (≥ 2% and ≥ 24 UFs).
- **Interval:** ± **0.8 pp**. Source: the same rule as §3, i.e. the largest absolute error in the same two backtests
  at the same checkpoints, which was 0.782 pp, rounded up (FINDINGS P11).
- **Role:** the main system's number is the project's projection. The backup is published **only if the main system
  fails** (no projection line for 10 minutes after the gate opened, or a crash). The switch is recorded with its
  time, and every post made from it says that it comes from the backup system.
- **Helpers' runs** of the same notebook are watermarked "BACKUP · NÃO PUBLICAR" and are never published.
- **Evaluation:** as §4, with the ±0.8 pp criterion.

## 8. Credit
The municipal swing model was inspired by Rodrigo Mahlmeister's live projection of the 2026 first round, as reported
by NeoFeed. No code from his project was used.
