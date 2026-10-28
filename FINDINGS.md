# Findings

**Rule** · Every claim records the run that produced it (report folder, tool version, protocol state). Revised claims
are kept as corrections and are never deleted.

## Calibration (2022)

### C1 · 2026-10-11 · smoke run, RR + AC only (v0.1, `reports/2022_t1_20261011-070833`)
- I1 to I7 found 0 violations in 3,392 sections.
- The clock offsets were inferred as AC +2 h and RR +1 h, which matches the official time zones.
- The freeze clock window gave −0.76 pp, p = 0.31.
- It is a pipeline check only.

### C2 · 2026-10-11 · full run, all 28 files, unadjusted test (v0.1, `reports/2022_t1_20261011-074543`)
- **Coverage:** 472,028 sections (472,024 counted).
- **The tally rebuilt from the BUs matches the official 2022 result:** Bolsonaro 43.20%, Lula 48.43%.
- **Integrity:**
  - I1 to I4 and I7: 0 violations.
  - I5: 113 duplicate box serials, of which 14 are in Brazil; the rest are abroad, where ZZ boxes are reused across
    cities.
  - I6: 17 violations. All 17 are sections with **no** opening or closing time recorded, i.e. BU recovered by a
    contingency procedure. They are not clock errors. → The check was split into I6 (complete clocks) and I6b
    (informational).
- **Freeze clock window (no freeze happened in 2022):** −0.008 pp, p = 0.88.
- **Calibration failure.** The 20:08 to 21:16 placebo window **rejected** (−0.244 pp, p = 0.001), and the 17:52 to 19:00
  window was borderline (p = 0.02). The unadjusted test therefore produces false alarms in late windows.
- **Cause found (exploratory, 2022 only).** Within each location, two things move the margin residual:
  - **close delay:** −0.68 pp for sections closing more than 2 h late (queues);
  - **section-rank quintile:** −0.72 pp for the newest sections.

  Late windows hold late-closing sections (median close delay 20 min, against 4 min elsewhere). Both causes are
  fixed before transmission.

### C3 · 2026-10-11 · full run, covariate-adjusted test (v0.2, `reports/2022_t1_20261011-081804`; the numbers are identical to `080302` thanks to the fixed seed, but that run had a plotting bug)
- **Primary (adjusted margin, freeze window):** −0.056 pp, p = 0.43.
- **All 15 adjusted tests** (5 windows × 3 metrics) have p ≥ 0.10. The failing placebo now gives −0.037 pp,
  p = 0.70.
- **Integrity:** I6 has 0 violations; I6b has 17; I5 has 14 cases in Brazil, to be checked case by case. In the two
  inspected cases, one of the paired sections has no clock data, which fits BU recovery onto another box.
- **Over-dispersion of z:** 1.16, i.e. real sections vary 16% more than binomial noise. The permutation tests are
  immune to it.
- **Observation for communication.** In 2022 the arrival-order curve crossed (Lula overtook Bolsonaro) at about
  20:00 BRT, **inside the same clock window**, with no freeze and no within-location anomaly. A crossing or a bend
  in the curve is the expected result of regional arrival order and is not evidence on its own.

**Calibration conclusion:**
- The adjusted test behaves as a valid test on 2022: no rejections in the primary, sensitivity or placebo windows.
- It still detects a 5% shift injected into synthetic data in which the same queue confounder is present.
- The protocol is ready for the author's review and freeze.

### C4 · 2026-10-11 · calibration of the round-2 forensic protocol on the 2022 run-off (`reports/calibration_round2_2022/`)
- **H3:** no nationwide reception gap of 5 minutes or more before 95% received. For contrast, 2026 round 1 had a
  27.5-min gap.
- **H1 bin scan:** 18 ten-minute bins, adjusted margin; 0 rejections at Bonferroni (0.01/18), and 0 at the nominal
  0.01 (min p = 0.011).

## Live publication and collector

### E3 · what TSE publishes live (`exploratory/e3_live_publication_2026.py` and probes of resultados.tse.jus.br)
The base is `https://resultados.tse.jus.br/oficial/`. The 2026 round-1 files are still online, with codes pleito
3220, election 6257, office 1; the round-2 election is 6258.

| File | Path | Content | Usable for the first 2–5%? |
|---|---|---|---|
| config | `comum/config/ele-c.json` | elections, codes, directory templates | yes |
| results BR / UF / municipality | `ele2026/6257/dados/<uf>/<uf>[<mun>]-c0001-e006257-u.json` | votes per candidate for that area | **yes** |
| progress (andamento) | `ele2026/6257/dados/<uf>/<uf>-e006257-ab.json` | per municipality: sections totalised (`st` of `ts`), electorate counted, time `ht` | **yes** |
| section configuration | `ele2026/arquivo-urna/3220/config/<uf>/<uf>-p003220-cs.json` | every section with a time `da/ha` | no, see below |
| per-section aux | `ele2026/arquivo-urna/3220/dados/<uf>/<mun>/<zona>/<secao>/p003220-...-aux.json` | reception time `dr/hr`, status, the box's original files (`bu.dat`, `rdv`, `log`, `vota`) | no, see below |
| old `dados-simplificados/...-r.json` | | | 404 in 2026 |

- **Municipal results are near real time.** In SP, a municipality's totalisation time (`ht` in `ab`) comes a median
  of 2.1 min after its last BU reception (95th percentile 8.3 min). Municipal totalisations continued from 19:00 to
  19:31 during the freeze of the national publication, were absent from 19:32 to 19:58 (matching the reception gap,
  F1/H3), and resumed at 20:03.
- **Section-level files lag by hours, at least in their final state.**
  - The `ha` times in `cs.json` start only at 20:30, with a median lag of 4.5 h after reception. 0% of sections
    carry a `cs` time before 20:08, so `ha` marks the later publication of the box files, done in about 36 batches
    (largest batch: 40,750 sections at 22:59).
  - Whether `cs.json` changed **during** the count cannot be told from its final state. Its live behaviour must be
    checked in TSE's simulation environment (`resultados-sim.tse.jus.br`) or at the start of round 2.
<!-- phase2:start -->
  - *(Edited 2026-10-11: a description of a third party's implementation was removed. That project is now private
    to protect its author's work.)*
<!-- phase2:end -->

### E4 · 2026-10-11 · live collector checked against 2026 round 1 (`exploratory/e4_live_collector_check_2026r1.py`)
- **Load:** `python -m tally live --election 6257 --once` made 85 fixed requests (BR, 28 UF results, 28 progress, 28
  section-configuration files) plus 5,757 municipal result files.
  - Time: about 3.5 min when everything is new (48 workers). With the state saved, a cycle with no change took
    3.5 s (85 × HTTP 304).
  - Failed municipal downloads (3 in one run) are now retried in the next cycle.
- **Reconciliation, exact:**
  - the 5,757 municipal files sum to the national file and to the official totals (56,104,503 and 53,879,538);
  - for all 5,716 municipalities with BUs, live votes equal the sum of the section BUs and the progress-file section
    counts equal the bweb counts;
  - the 41 extra live municipalities are abroad (ZZ), with 42 sections and 0 votes.
<!-- phase2:start -->
- **Pipeline:** projections on the final live state return 51.009% against the official 51.012%. The difference is
  the municipalities missing from the 2022 base.
<!-- phase2:end -->
- **Storage:** content-addressed with SHA-256, gzipped, plus an append-only `fetch_log.jsonl`; one full snapshot is
  about 15 MB. `load_state(archive, as_of_utc)` rebuilds what was known at any moment.

## Protocol freeze
- **When:** 2026-10-11T10:59:07+01:00, by the author's decision. No 2026 analysis had been run before this
  point.
- **SHA-256 of the protocol files at freeze:**
  - `METHODOLOGY.md`: `052a42b0914a0088131887d36753316aa9925839c18d22cbc20ecf5d9f21cc33`
  - `config/analysis.json`: `7d01e20aa88a1fdf8ab47f710a1c5b2bf5d607f080846c2ff6c0074c5756b642`
  - `tally/temporal.py`: `d00fbf8de8b7c314549cb7274b1d2b133747a251df3fb94e3b8d5196e27b61a7`
  - `tally/residuals.py`: `fae15ddf60f36641e6f861f8a4ebf8c924ca35779e28ea9830efc078dd2a2877`

## Round-2 protocol freeze (PREREGISTRATION_ROUND2.md)
- **When:** 2026-10-20T13:57:42+01:00, by the author's decision, before the run-off of 25 October 2026. Git tag
  `round2-prereg`.
- **SHA-256 of the frozen files, as published in this repository:**
  - `PREREGISTRATION_ROUND2.md`: `cd9e80199e6bcafe316227b39b787f62b0aa556764c5ee786dd5cf799266cc1e`
  - `config/round2_forensics.json`: `34d1b55a2a1987db66cdadf1a7b11ff4cbeafe85de9d9b7612d9c360f28d8d7d`
  - `tally/temporal.py`: `6b039f548023761a728e1a7429e6a5777bee2bb42c281b52264b04e4b1c94674`
  - `tally/residuals.py`: `fae15ddf60f36641e6f861f8a4ebf8c924ca35779e28ea9830efc078dd2a2877`
  - `tally/integrity.py`: `0cef79490b0d1ecfc5540ec936f63d296d23d55765a0e7a7953055f353d0ebe1`
  - `tally/live.py`: `521df435477fc2190a47100a7de81d31ddd851e2e8a182b4d0604329418e4101`
- From here on, any change to these files is a logged deviation.
- **Phase B (live projection of the run-off), frozen at the same time,** is committed by hash in `commitments/`.
  Its OpenTimestamps proof (the `.ots` file there) was submitted at 2026-10-20T14:27+01:00. The files
  will be published after the election.
  - **Revealed on 2026-10-28** (author's decision, after the round-2 audit below). The frozen copies from tag
    `round2-prereg` are in `commitments/reveal_round2_prereg/`, and all 8 lines of
    `commitments/round2_projection.sha256` verify there. Since the reveal, the published
    `PREREGISTRATION_ROUND2.md` is the lab version (with §5), SHA-256 `b4c0fc…65b5` (full hash in the list
    below). The earlier published hash `cd9e80…6cc1e` applies to the pre-reveal file without §5. No other frozen
    file changed.
<!-- phase2:start -->
- **Deviation (wording only):** the lab `PREREGISTRATION_ROUND2.md` §5 says the hash "will be published here". It
  was published in `commitments/` instead, because that file was already frozen. The owner also decided on
  2026-10-20 that phase B may now be named in public.
- **Lab freeze of the projection (PREREGISTRATION_ROUND2_PROJECTION.md), same time, lab tag `round2-prereg`.**
  SHA-256 in the lab:
  - `PREREGISTRATION_ROUND2.md` (lab version, with §5): `b4c0fc2e4753d8b60ec6f6916a3101e977e2de19fa70df8ba5d21e2b3fa865b5`
  - `PREREGISTRATION_ROUND2_PROJECTION.md`: `b1d3837f07fe3e3f73fb21ea9c7c429d23627548aa7d65cc16040bf1a9d3f486`
  - `config/round2_projection.json`: `e1a8c5ed560a02f43dc3fc5d9aefec09f140cc43afa2ca3e5f336fb5e84149a3`
  - `tally/project.py`: `079589b0cc8b123c50aafd890b2f11af19a3f9249f471537565f1ef3c18e108b`
  - `tally/live_projection.py`: `27b05b2de2cb169281d97b4fe100f43be09e131f0659b9b92402ac979550cda1`
  - `tally/live.py`: `521df435477fc2190a47100a7de81d31ddd851e2e8a182b4d0604329418e4101`
  - `colab/tally_colab.py`: `6fe773bde0c99d3be7423d6e255c9705909cd204333ca895d3719094213ac5a9`
  - `colab/make_notebook.py`: `f6c79735f6f93b9564ebb3600ffde7c049dabf002731fce5f1e50e2af4114ebe`
<!-- phase2:end -->

## Round-2 addendum H6r2: extended voting hours (PREREGISTRATION_ROUND2_EXTENSION.md)
- **Why:** on 25 Oct 2026 TSE extended voting until 19:00 BRT in some places. The author asked for a check of
  the extended sections, for transparency.
- **When fixed:** 2026-10-25T23:59:34Z (20:59 BRT), during the count. Partial **municipal** results had been seen
  (about 86% of sections counted), but **before** TSE published any round-2 bweb file: TSE's open-data catalogue
  listed round-1 files only.
  - **Correction (2026-10-26):** §0 of the addendum says "about half of sections counted". That is wrong: about
    50% was the count when the addendum was proposed (20:30 BRT); at the time it was fixed and timestamped it was
    about 86%. The hashed file is left unchanged; this note is the correction. It does not affect the tests, which
    use section-level data that did not exist yet.
- The tests use section-level data only. This is an addendum, not part of the 20 October freeze, and is reported
  as such.
- **Hashes** (`commitments/round2_extension.sha256`, OpenTimestamps proof submitted to 4 calendars at 23:59 UTC):
  - `PREREGISTRATION_ROUND2_EXTENSION.md`: `5e85ad817803083f799c35aff7608b153554aefdb76bdc6da45094179d4d07dc`
  - `tally/extension.py`: `3fa9ac6cf0dbc2272666fb5375e86dc52bb53d6f0c6987212b2317aa68c4d09b`
- The code was checked on synthetic data only, before fixing. The 2022 calibration (§4) runs before the 2026 data.

## Round-2 addendum H7r2: ballot-box logs vs ballot-box reports (PREREGISTRATION_ROUND2_LOGS.md)
- **Why:** voting was extended on election day, and the author asked for a stricter audit by two independent
  methods, cross-checked.
  - TSE also publishes each box's event log, with a time for every vote, on its results site.
  - H7r2 checks, section by section, that the logs agree with the bweb files: coverage, votes, close time, box
    number and the extended set.
  - It also reruns H6r2 with the extended flag taken from the logs.
- **When fixed:** 2026-10-26T15:53Z (12:53 BRT), **before** TSE published any round-2 bweb file. TSE's open-data
  catalogue listed round-1 files only, which was checked just before stamping.
  - Before fixing, only Roraima's logs were examined, and only against **round-1** bweb. That calibration is
    reported in §4 of the addendum.
- **Hashes** (`commitments/round2_logs.sha256`, OpenTimestamps proof submitted to 4 calendars):
  - `PREREGISTRATION_ROUND2_LOGS.md`: `690269f3b68fcd1f27a5fffbc9a1159da65efd24fbeafc775186c1be100046f1`
  - `tally/urna_logs.py`: `84b077535d3443fc0b5733a0be4bd99747506e0acf83eea95f3057aa0b48b51c`
- A third party (repository "urnas-tardias") published a log-based count of late votes on 26 Oct. It was read
  before this addendum was written, and one of its example logs was checked by hand. Its method is independent of
  this one.

## Round-2 addendum H8r2: signature search (PREREGISTRATION_ROUND2_SIGNATURES.md)
- **Why:** the box is a black box. Its BU, RDV and log come from the same software, so consistency checks
  (H1r2–H7r2) cannot show that it counted correctly. The author asked for a search for **signatures**: patterns
  that independent human voters would not produce.
  - Box logs, S1–S7: votes too fast, manual enablings, periodicity, repeated voter trails, fingerprint scores,
    synchrony across boxes, software load.
  - Section transfers from round 1 to round 2, T1–T4: too homogeneous, too uniform, against 2022.
- **Stance:** the project never states that the result is correct.
  - If no signature is found, the result is **"no signature found so far"**, with these data and methods. Other
    methods and analyses will follow.
  - A signature is reported as an "unexplained pattern", with its sections listed for a physical check.
- **Design:** the UFs are split at random (seed 20261026) into a discovery half and a locked confirmation half.
  - The hunt in the discovery half is free, and every look is logged.
  - Each candidate signature is written as a test and timestamped, then run once on the confirmation half.
- **When fixed:** 2026-10-26T22:28Z (19:28 BRT), **before** TSE published any round-2 bweb file and before any
  per-section round-2 figure was analysed.
  - Seen before fixing: the national totals of both rounds, and the event vocabulary and round-1 lines of one RJ
    log.
  - The synthetic tests found one defect in T3 (false alarms on clean data). It was fixed before the freeze.
- **Hashes** (`commitments/round2_signatures.sha256`, OpenTimestamps proof submitted to 4 calendars):
  - `PREREGISTRATION_ROUND2_SIGNATURES.md`: `f1278be56979d8a7d3fe6bea9d274156cd10782704c20e4de31f0574db9c8f56`
  - `tally/signatures.py`: `db7de504a0069f0e4f21481ad6c730447be4f7633e867060d9bdf53fd32b4666`
  - `tally/full_logs.py`: `df2af2bed7043ade9afa48ef317b41cb1681181a526b02e204c47b87441eecf3`
  - `tests/test_signatures.py`: `2dddf40f551e20b2a3e03aaa2f154c8435a8e1448b4e8e5f66ddcd43237fd8fa`

## Confirmatory (2026, round 1)

### F1 · 2026-10-11 · full run, protocol frozen (v0.2, `reports/2026_t1_20261011-133033`)

**Coverage:**
- 28 of 28 files, all SHA-512 verified against TSE.
- 499,206 sections, all counted (`CD_TIPO_URNA` = 1); 497,897 are in Brazil.

**H4: integrity and reconciliation (deterministic)**
- **R-22 and R-13: the sum of the 499,206 section BUs equals TSE's official totals exactly.** Both differences are
  0 votes:
  - Flávio Bolsonaro: 56,104,503 votes (47.03%);
  - Lula: 53,879,538 votes (45.16%).

  The transmission and totalisation layer is internally consistent, to the vote.
- I1 to I5 and I7: 0 violations. Unlike 2022, no ballot-box serial is shared between sections.
- **I6 (clock order): 60 violations.**
  - All 60 are "BU emission after TSE reception" after clock conversion, by 0.1 to 54.5 minutes. There are none on
    opening or closing.
  - 53 are in MT, 55 in UTC-4 municipalities.
  - In those municipalities, some boxes run on the BRT clock and others on local time. In Querência (MT), for
    example, 41 boxes open at 07:xx and 13 at 08:xx.
  - The tool infers one offset per municipality, so it shifts the BRT-clock boxes by a spurious +1 h.
  - **This is an artefact of the tool's clock normalisation, not of the data.** Read on the box's own clock, those
    sections close at 17:00 and are received minutes later.
  - Effect on the tests: negligible. It affects the close-delay covariate of about 60 of 497,897 sections.
  - Fix planned for v0.3: infer the offset per box instead of per municipality.
- I6b: 2 sections with no opening or closing time.

**H1: primary (adjusted margin, freeze window 19:00 to 20:08 BRT)**
- Effect −0.085 pp, p = 0.40, from 7,687 informative locations (25,828 sections inside the window, 34,863 outside).
- **Not rejected.** There is no evidence that sections received during the freeze differ from their own
  polling-location siblings.
- Decision rule §4.1: condition 1 fails, so no anomaly signal. Sensitivity windows: p = 0.85, 0.08 and 0.63.

**H2: secondary, Holm over 2 tests**
- Adjusted `a_resid`: p = 0.28.
- Adjusted turnout: p = 0.025, Holm-adjusted 0.049. **Not rejected** at alpha = 0.01.

**H2u: unadjusted**
- It rejects in every window, including both placebos (p ≤ 0.002, effect −0.34 to −0.51 pp).
- As predicted by the 2022 calibration, the unadjusted test is confounded by queues and section rank, and the
  confound is stronger in 2026.
- It is reported for transparency and has no evidential value.

**Placebo windows (adjusted):** none rejected at 0.01. The 17:52 to 19:00 window gave p = 0.047 for margin and
p = 0.044 for turnout.

**H3: did reception stop? (descriptive) · THE NULL IS CONTRADICTED BY TSE'S OWN TIMESTAMPS**
- **Gap:** no BU in any UF carries a TSE reception time between **19:31:50 and 19:59:22 BRT** (27 consecutive
  minutes with zero receptions). In 2022, at the same clock time, the rate never fell below 2,341 per minute (median
  3,387).
- **Slowdown before the gap:** receptions fell from about 5,000 per minute to about 1,700 per minute at 19:21–19:22.
- **After the gap:**
  - a catch-up burst of about 19,000 sections in 19:59–20:02;
  - then about 500 per minute, the tail of the count.
- **Consistency with the published figures:** 85.2% of sections had been received before the gap; TSE resumed
  publication at 20:08 showing 84.96%. The press reports "stuck at ~64% from ~19:00", while sections were still
  arriving at a high rate until 19:21 (70.8% received by 19:10). So publication stalled first, and reception (or its
  recording) paused from 19:32.
- **Interpretation (carefully):** `DT_BU_RECEBIDO` is TSE's own record of when each BU was received or registered.
  The gap shows that this registration paused for 27.5 minutes in every UF at once.
  - This is consistent with TSE's statement that "a security protocol was activated" when abnormal data flow was
    detected.
  - It is **not** consistent with the reading that only the *publication* paused, if `DT_BU_RECEBIDO` stamps network
    arrival. TSE's *leiame* does not define the field precisely.
  - The question is factual and should be put to TSE: what does `DT_BU_RECEBIDO` stamp, and what happened between
    19:31:50 and 19:59:22?

### E1 · exploratory, not pre-registered (`exploratory/e1_reception_gap_2026.py`, output saved in the report folder)
Did the sections around the gap differ from their own siblings? The same adjusted within-location test was used.

| Window | Margin, adjusted | Turnout, adjusted |
|---|---|---|
| slowdown 19:21–19:32 | −0.19 pp, p = 0.11 | p = 0.34 |
| catch-up burst 19:59–20:03 | −0.19 pp, p = 0.18 | p = 0.30 |
| slow tail 20:03–20:30 | +0.12 pp, p = 0.33 | p = 0.17 |

None is significant. The sections whose registration was delayed by the gap look like their neighbours.

### E5 · exploratory: every pause on election night (`exploratory/e5_all_gaps_2026r1.py`, output in the report folder)
The question was whether the 19:32–19:59 gap was the only one. The method looked for runs of 2 minutes or more with
zero events, Brazil only, from the first reception until 99.5% had been received.

| Timeline | Pauses of 2 minutes or more |
|---|---|
| 2026 r1, BU reception (`DT_BU_RECEBIDO`) | **18:02–18:08 (6 min)**, **18:50–18:53 (3 min)**, **19:32–19:59 (27 min)** |
| 2026 r1, municipal totalisation (`ht` in the progress files, converted to BRT) | 18:02–18:08 (6), 18:50–18:54 (4), **19:33–20:03 (30; one municipality completed at 19:45)**, plus short pauses at the start and the tail |
| 2022 r1, BU reception (reference) | 18:14–18:20 (6 min), 20:31–20:35 (4 min) |
| 2022 r2, BU reception (C4) | none of 5 min or more |

- **Short pauses are routine.** Pauses of 3–6 minutes happened in 2022 too. Reception and municipal totalisation
  stop and resume **together**, so these pauses come from the system, not from where the data come from.
- **The 19:32–19:59 pause is the outlier.** It lasted 27 minutes, 4–5 times longer than any pause in 2022, and both
  reception and totalisation stopped nationwide.
- **Official account** (TSE, as reported by CNN Brasil and Poder360):
  - the national ("Brasil") view of the presidential result froze at 64.81% from about 19:14 to 20:04, about 50 min;
  - the state views kept working;
  - the cause was congestion in data processing.

  The data add a nuance. Reception was already slowing at 19:21, and it stopped from 19:32 to 19:59. Municipal
  totalisation stopped from 19:33 to 20:03. So during part of the national freeze, the state views could not have
  advanced either, because there was nothing new to show.
- **Pre-registered window:** the official freeze, 19:14–20:04, lies inside the pre-registered window of 19:00–20:08
  (F1). Its start is 14 minutes later, covered by the +15 min sensitivity window.
- **A clock detail found here:** the `ht` times in the progress files follow each municipality's **local** clock. In
  UTC-4 municipalities they lag BRT by 1 hour. They must be converted before any national timeline is built.

<!-- phase2:start -->
### E2 · exploratory: early-count coverage (`exploratory/e2_early_coverage_2026.py`), input for the round-2 projection
- **First 2%:** 9,957 sections, received by 17:28 BRT; 23 of 27 UFs already have 30 or more sections. The first 5%
  (by 17:39) covers 26 UFs, and the first 10% covers all 27.
- **The raw early count is biased.** At 2%, Flávio reads 50.61% against a final 47.04% (+3.6 pp), because PR is 26%
  of the early sections. A projection must model each section against its own baseline, never extrapolate the
  partial tally.
- **Minor candidates:** at 2%, about 2% of each one's national vote has been counted (55k to 70k votes each); at 5%,
  about 5%. The early sample for every minor candidate is concentrated in PR (MG for Zema). Their transfer is
  therefore learned first from Paraná voters.

<!-- phase2:end -->

### Overall conclusion of the 2026 round-1 analysis
1. The published national result is exactly the sum of the 499,206 public section BUs.
2. Sections received during the freeze, during the slowdown, right after the gap and in the tail are statistically
   indistinguishable from sections in the same polling location received at other times.
3. There **was** a real, nationwide 27.5-minute pause in TSE's reception records. It is an operational event that
   deserves an official explanation, and the data show no trace of it in the votes.
4. **What this does not cover** (METHODOLOGY §6): manipulation inside the ballot box applied uniformly, which no
   section-level statistic can see.

## Confirmatory (2026, round 2)

### F2 · 2026-10-28 · frozen round-2 audit H1r2–H5r2 (`exploratory/e27_round2_audit.py`, `reports/round2_2026/`)
- **Data:** TSE's round-2 bweb (stamp `261020260742`, first seen 2026-10-28T08:07Z), 28 files verified against
  TSE's SHA-512 and logged in `data/manifest.jsonl`; 499,205 sections. Parameters from the frozen
  `config/round2_forensics.json`; official totals and municipal results from the election-night collector archive.
- **H1r2** (10-min reception bins, covariate-adjusted): 25 bins, **0 rejections** at Bonferroni (0.0004) and 0 at
  nominal 0.01; minimum p 0.015 (20:40 bin).
- **H2r2** (publication freezes): no period qualifies under the frozen definition. The 17:07–19:01 stillness had
  0.02% of sections received.
- **H3r2** (reception gaps): one nationwide gap, **17:08 to 19:03 BRT (115 min)**: the extension of voting hours.
  Reported as a process fact.
- **H4r2** (integrity): I1–I5 and I7, 0 violations; I6, 8 (PA/PR, TSE reception 9–49 s before the box's emission
  time: box clock offset, as in round 1). **The sum of the BUs equals TSE's final national file exactly:** 22
  59,826,041; 13 64,256,232.
- **H5r2** (live vs BU): in all 4,125 municipalities at 100% in the archive, the live result equals the sum of the
  BUs. 1,632 municipal files were not final when the collector stopped and cannot be compared.

### F3 · 2026-10-28 · H7r2, box logs vs bweb (`exploratory/e28_h7r2.py`, `reports/h7r2/`)
- H7a: every bweb section has a log entry; 43 log entries have no bweb row.
- H7b: 1,464 vote mismatches. 1,422 are a box replaced during voting (the published log covers the replacement
  only). Of the other 42:
  - 27 are abroad sections where TSE lists no log;
  - 3 boxes have one "Voto confirmado" line more than "voto computado" (the bweb equals the confirmed count);
  - 12 Brazilian boxes have a published log with no voting events: 5 are a contingency box running the data
    recovery application (RED), 5 a contingency box loaded after 17:00 with no votes, and 2 have no raw log kept.
    The result was recovered from the original box's media after closing, a documented procedure.
- H7c: 0 close-time mismatches over 60 s. H7d: 32 (27 abroad, 5 of the 12 above). H7e: 11 (6 abroad on local
  clock; 5 Brazilian boxes whose closing was completed by recovery).
- Extended sections (close ≥ 17:30 BRT): 7,612 by bweb, 7,613 by log.
- Exploratory cross-check: votes for 22 and 13 in the bweb equal the section `bu.dat` files in all 499,174 joined
  sections.
- The 12 boxes are listed in `reports/h7r2/h7_discrepancies.csv` for comparison with the printed BUs.
- Not yet run: H6r2 with the extended flag taken from the logs (H7r2 §3).

### F4 · 2026-10-28 · H6r2, extended voting hours (`exploratory/e29_h6r2.py`, `reports/h6r2/`)
- Frozen `tally/extension.py`; 10,000 permutations, seed 20261025, Bonferroni 0.01/7.
- **Calibration §4.1** (2022 run-off, 333 real late closers, no extension that year): H6a p 0.34 / 0.026 / 0.21;
  H6b not computable; **H6c false alarm** (p 6.6e-5), so by the fixed rule H6c is descriptive only in 2026.
  §4.2 (200 placebo label draws) has not been run.
- **2026 primary** (17:30 BRT, 7,612 extended of 497,708):
  - **H6a share for 22: +0.049 pp, p 0.029, not rejected** (the headline);
  - H6a turnout +0.185 pp and blank/null +0.083 pp, p 0.0001, rejected: extended sections gained slightly more
    turnout and blank/null than on-time sections of the same municipality, both well under half a point;
  - H6b: none rejected;
  - H6c (descriptive): 22 of 7,612 flagged, p 0.060, listed in `h6c_flagged_2026_primary.csv`.
- Sensitivity runs (18:00 BRT; local clock) give the same decisions.

### E25–E26b · exploratory: the 17:00–19:00 window (`reports/h8r2/hunt_log.md`, entry of 2026-10-28)
- Question (author): could boxes have been altered at scale between 17:00 and 19:00 BRT, while TSE recorded
  almost no receptions?
- No `bu.dat` was emitted before its box closed. BU emission more than 30 min after closing is much more frequent in
  the 2026 run-off (686 boxes by the bweb) than in 2022 or 2026 round 1 (about 40 to 117).
- In the full logs of 2,703 late boxes and 2,802 controls, between closing and `bu.dat`: **0 votes computed,
  0 voters enabled, 0 urn changes**.
- The delay sits in the post-voting poll-worker registration step (over 30 min in 626 boxes, against 1 in round 1).
  77% of those boxes are in a polling location where another section was extended (3.3% of all boxes); none was
  itself extended. The cause of the wait is not in the data.

### Overall conclusion of the 2026 round-2 analysis
1. The published national result is exactly the sum of the public section BUs, and the bweb, the section `bu.dat`
   files and the box logs agree.
2. No pre-registered test of reception time rejected; the extended sections show no difference in the share for
   either candidate.
3. In the boxes that issued their BU late, no vote was taken after closing.
4. **No signature found so far.** This does not state that the result is correct. A change made inside the box
   software before the BU is signed would not show in any of these files (METHODOLOGY §6). The independent checks
   for that are the printed BUs and the integrity-test reports.

## Protocol deviations
- **2026-10-11 (non-substantive, code path only).**
  - What happened: the freeze edit, made with Windows PowerShell 5.1, saved `config/analysis.json` with a UTF-8 BOM,
    and the first 2026 run failed to parse it before any analysis was done.
  - Fix: `tally/config.py` now reads the file as `utf-8-sig`.
  - What did not change: the frozen file. Its SHA-256 still matches the freeze record (`7d01e2…b642`), and no
    analysis parameter changed.
- **2026-10-11 (additive code change after the round-1 confirmatory run; disclosed when preparing the first git
  commit).**
  - `tally/temporal.py` no longer matches its round-1 freeze hash (`d00fbf…61a7`, now `6b039f…4674`), because two
    new functions were added for the round-2 protocol: `reception_gaps` and `scan_bins`.
  - The round-1 results (F1) were produced before this change.
  - The function used by H1, `window_test`, and its helpers were not edited. This cannot be proven by hash, because
    no version control existed at the time; it is the author's statement.
  - The other three frozen files still match their hashes (`METHODOLOGY.md`, `config/analysis.json`,
    `tally/residuals.py`).
  - **Lesson:** from now on, freezes are git tags, so any later change is visible as a diff. The covariate adjustment (METHODOLOGY §4.2) was added during calibration, before the freeze and before any
2026 analysis. That is allowed by §7.

- **2026-10-24 (phase B, presentation only, found in the final pre-election test).**
  - What changed: in the media card (`make_card` in the backup system's `colab/tally_colab.py`; the same in the
    teaching notebook and in `tools/card_local.py`), rows logged before the first result are no longer drawn.
  - Why: those rows have a raw share of 0%, which pulled the chart's axis down to 0% and flattened the projection
    line.
  - What did not change: the model, the publication gate, the interval and the logged projections.
  - Verification: the committed version is the one at tag `round2-prereg`. Both versions will be published, so the
    hash in `commitments/` still verifies against the frozen file. The diff is three lines.

<!-- phase2:start -->
## Phase 2: run-off projection (private until after the election; not part of the forensic protocol)

### P12 · 2026-10-25 · election night and evaluation against the final result
- **Voting extended to 19:00 BRT** in some places. Abroad results appeared at 17:07; Brazil from 19:01.
- **Gate opened at 19:34 BRT** (7.7% of sections counted, 24 UFs) with SP, RJ and SE below 1%. The first projection
  was Flávio Bolsonaro 47.88% [47.18, 48.58]; it then rose to about 48.5% by 19:48 and stayed at 48.2–48.7%.
- **Not posted at the gate, by the author's decision:** the arrival order was unlike the backtests, and the
  projection was still moving. Posting is not required at the gate, so waiting is not a deviation.
- **Posted on X and WhatsApp at 20:38 BRT** (23:38 London; X timestamp "11:38 PM · Oct 25, 2026"), using the card
  of 20:26 BRT: **Flávio Bolsonaro 48.3%, Lula 51.7%**, ±0.7 pp, called for Lula.
  - The Colab backup showed 47.9 / 52.1 around the gate (19:37–19:40) and 48.40 at 20:26.
  - The first card generated was the Colab's, at 19:35 BRT (7.0% of the electorate, 24 UFs): 47.6 / 52.4, ±0.8 pp,
    Lula. Its error was −0.62 pp. It was not posted.
  - Correction (2026-10-26): an earlier draft of this entry put the Colab's 47.9 "at about the same count" as the
    posted card. That is wrong; the figures above come from the Colab log.
- At 21:09 BRT (97.7% of sections) the official partial was Flávio Bolsonaro 48.26%.
- **Final result (100% of sections, TSE file of 23:27:02 BRT): Flávio Bolsonaro 48.2148%** of the two-candidate
  vote, Lula 51.7852%. The posted 48.3% was 0.09 pp off.
- **Evaluation (pre-registered):** error = estimate − final, at the first projection cycle at or after each level.
  The gate opened above 5%, so the 2%, 3% and 5% columns are that first cycle.

| System | first cycle | 2% / 3% / 5% | 10% | 20% | 50% | max abs error | all inside interval |
|---|---|---|---|---|---|---|---|
| Main (±0.7 pp) | 19:33:59 at 7.67% | −0.34 | −0.30 | +0.39 | +0.10 | 0.48 (19:53, 17.2%) | yes, 493 of 493 cycles |
| Colab backup (±0.8 pp) | 19:35:16 at 6.99% | −0.62 | −0.04 | +0.51 | +0.13 | 0.67 (19:54, 16.1%) | yes, 150 of 150 cycles |

  - **Both systems called Lula at every cycle and never left their pre-registered error band.** The result is a
    clean pass.
  - The two systems measure "counted" differently: the main one by sections, the Colab one by electorate.
  - The common pattern: both read low at the gate, while SP and RJ were missing, then high (+0.4 to +0.5) at about
    20%, and converged from about 50%.
  - The Colab run stopped at 21:00 BRT as configured (`STOP_AT_BRT`), at 82.2% counted, reading 48.20 (−0.02 pp).
  - Sources:
    - main: `data/live/ele2026_e006258/projections.jsonl`;
    - Colab: `reports/night_logs/colab/projections_e6258.csv`, SHA-256 3bfed668…5555, from the author's Drive.
  - Backup: `..\tally-forensics-backup\2026-10-26_election_night\` (SHA-256 538f8139…01f7d2). That archive
    accidentally holds the 24/10 Colab test CSV under the same name; the archive's `NOTE.txt` explains this.
- **Runtime:** the Terminal panel's start-up Ctrl-C killed both processes while importing. Both ran as background
  processes, with logs in `reports/night_logs/`. The collector was restarted at 17:18 with `--until 23:59`, because
  of the extension; there was no data loss, since TSE had published nothing new.

### P11 · 2026-10-20 · the Colab model on the P5 backtests; coverage gate; freeze (`reports/p11_colab_model_backtest/`)
- **Question:** the backup Colab model (swing only, `k_mun = 2000`, `k_uf = 10000`) had been checked only against
  round 1 itself. How does it do on the two backtests used for the main rule (P5)?
- **Method:** `exploratory/p11_colab_model_backtest.py`. The count is replayed in real TSE arrival order, and the
  model sees only municipal aggregates. `tally_colab.project` is unchanged.
- **Errors (pp):**

| Backtest | 2% | 3% | 5% | 10% | 20% | 50% |
|---|---|---|---|---|---|---|
| 2022 r1 → 2026 r1 | −0.449 | +0.202 | +0.286 | +0.612 | +0.782 | +0.387 |
| 2022 r1 → 2022 r2 | −0.708 | −0.587 | +0.013 | +0.322 | +0.452 | +0.524 |

  - The maximum is 0.782 pp, above the main rule's ±0.7, as expected for one model instead of the mean of two.
  - **Owner's decision:** the Colab system is pre-registered as the **backup**, with ±0.8 pp by the same rule (the
    envelope, rounded up).
- **Coverage gate (24 of 27 UFs with ≥ 1% counted):** it opened at **10% counted** in both backtests (17:33 BRT in
  the 2022 run-off; 17:52 in 2026 round 1). With 2% counted only 12–16 UFs had data.
  - **Owner's decision:** both systems use the gate of 2% **and** 24 UFs, so the first projection is expected at
    about 17:30.
  - Main model errors at 10% (P5): +0.370 and +0.034 pp.
- **Code change before the freeze:** `tally/live_projection.py` applies the gate (`min_ufs_with_1pct` in
  `config/round2_projection.json`). New test `test_coverage_gate_waits_for_enough_ufs`; 33 tests pass.

### P10 · 2026-10-13 · Colab model ignored uncounted votes from abroad (fixed)
- **Symptom (author's Colab run with the rate limit):** the projection stayed at 51.03% while coverage rose from
  71% to 99.3%. On round-1 data against itself it should converge to 51.0115%.
- **Cause:** the Colab model added abroad (ZZ) votes only once read and never projected the unread ones, so they
  counted as zero. ZZ is 186 cities and 0.27% of the two-party vote. Its cities are small, so with
  largest-first ordering they arrive last. With all of Brazil counted and abroad unread, the projection read
  51.0204%.
- **Fix:** ZZ is modelled as one more UF. Only municipalities missing from the base are taken as counted without
  projection.
- **Result:** the projection is 51.0115% with abroad unread, with only the 900 largest municipalities read, and with
  everything read.
- **Confirmed in Colab (author, 09:03–09:10 BRT):** the projection read 51.01% at every cycle, from 71.3% to
  100% coverage, with the queue draining 4,857 → 0 in 7 cycles of about 62 s. That run still showed
  "UFs 28"; the count is fixed to the 27 UFs in commit 1e19f41.
- **Correction (2026-10-13, prompted by the author):** abroad does **not** arrive last on election night.
  - In round 1, all 1,309 abroad sections carry a TSE reception time from 17:08:44 BRT (median 17:08:51), so
    they were in the very first batch, even for countries whose polls closed hours earlier (Asia, Oceania).
  - The "abroad last" situation came only from the test: the files were static and the queue was
    largest-first. Early on election night few municipalities have data, the per-cycle cap does not bind, and
    abroad is fetched at once.
  - The fix stays, because the model must never count unread votes as zero.
- **Main system:** not affected. `project.REGION` already maps ZZ to its own region, and the base includes ZZ
  sections.

### P9 · 2026-10-13 · TSE rate-limits bursts (HTTP 429): both collectors made polite
- **Evidence:** the Colab diagnostics over the last 2 h showed 32,192 × 200, **4,246 × 429 (Too Many Requests)**,
  1,190 × 304, and 39 log lines damaged by the old, non-thread-safe writer.
  - The 429s explain the failures of P8.
  - That day's tests made more than 32,000 requests in 2 h, including several full downloads of 5,757 municipal
    files at 32 parallel connections.
- **Risk for 25 Oct:** at the peak of the count, hundreds to thousands of municipalities change per minute, so the
  old behaviour could hit the limit exactly when the projection matters most.
- **Change (both systems):**
  - at most **15 requests/s** across all threads (helpers: 8/s; the main collector's workers go from 48 to 16);
  - on HTTP 429, **every thread pauses** for Retry-After (30 s if absent, at most 120 s);
  - at most **900 municipal files per cycle** (helpers: 450), **largest electorates first**. Deferred
    municipalities keep their last consistent snapshot (P8) and are fetched next cycle.
- **Offline tests (no request to TSE):**
  - 60 requests at a 20/s cap took 2.95 s;
  - after a 429 with Retry-After of 2 s, the next request came 2.00 s later;
  - with a cap of 2 per cycle, the two largest municipalities were fetched first and all 5 within 3 cycles;
  - `tests/test_live.py::test_per_cycle_cap_fetches_largest_electorate_first_and_defers_the_rest`.
- **Confirmed in Colab (author, 08:44–08:52 BRT, polite version):** diagnostics show 6,715 × 200, 580 × 304 and
  **zero 429s**; the 39 damaged lines are the old ones. The full download took 7 cycles of about 62 s at about
  14.5 requests/s.
- **Advice for 25 Oct:** no further full test downloads from Colab before the election. The base is cached on
  Drive, and a test on the final round-1 files is not needed again.

### P8 · 2026-10-13 · BUG found by the author's Colab test: failed downloads distorted the projection (fixed)
- **Symptom:** in Colab, on round-1 data (which should project exactly 51.01%), 37% and then 100% of requests failed,
  and the projection read **45.92%**.
- **Cause:**
  - in both systems, a municipality whose results file failed to download kept its progress figures ("counted")
    from the progress file but lost or kept stale votes;
  - it then entered the model as "counted with zero (or old) votes";
  - in the main collector, a network error other than URLError or TimeoutError (e.g. a connection reset during
    the read) could abort the whole cycle;
  - parallel writes to the log and to identical blobs were not thread-safe, which explains an intermittent test
    failure.
- **Fix:**
  - votes and progress now come from the **same** municipal file;
  - a municipality whose file was never read counts as not yet counted;
  - a failed download keeps the last consistent snapshot and is retried;
  - every network exception is caught per file;
  - log and blob writes take a lock;
  - Colab: no media card is produced in a cycle with more than 20% failed requests, and HTTP status counts are
    printed on back-off;
  - a diagnostics cell was added.
- **Regression tests:**
  - with 38% of municipal downloads failing (simulated 503s), the Colab projection is 51.0145% (63.7% counted)
    and returns to exactly 51.0115% after the retry;
  - `tests/test_live_projection.py::test_failed_municipal_download_counts_as_not_counted_not_as_zero_votes`;
  - 30 tests pass, three runs in a row.
- **Still open:** the cause of the failures in Colab. The HTTP status codes are needed: if they are 403 or 429,
  TSE is limiting requests from Colab's addresses after several full downloads on the same day. Run the
  diagnostics cell to check.
- **Re-test in Colab with the fixed notebook (author, 08:09–08:27 BRT):** 37 cycles with no failed requests
  (first cycle 58.8 s, then 0.3–1.2 s), the projection steady at 51.01%, and a card saved every 5 min. The earlier
  failures did not recur, which points to a transient problem rather than a block.
- **Protocol note:** this changes `tally/live.py` and `tally/live_projection.py`, which are listed in the round-2
  freezes. Neither pre-registration is frozen yet, and the change fixes a defect without touching the model.

### P7 · 2026-10-13 · independent Colab system (`colab/tally_live_independent.ipynb`)
- **Design:** a second live system, independent of the main one.
  - Base: round-1 **municipal result files** from TSE's results site, not ballot-box files.
  - Model: plain municipal swing, written separately.
  - Storage: Google Drive.
  - Publication gate: ≥ 2% of the electorate counted **and** ≥ 24 UFs with ≥ 1% counted (the owner's
    representativeness rule).
- **Local check against round 1:**
  - the base equals the official totals exactly;
  - the projection with everything counted is 51.0115%, equal to the official value;
  - a cycle with no change takes 1.4 s.
- **Access test run by the author in Google Colab:** all 4 files returned HTTP 200 in 77–415 ms (`ele-c.json`
  415 ms, national 77 ms, SP progress file of 525 kB in 165 ms, municipal file 115 ms). TSE's results site is
  reachable from Colab's servers, and faster than from the desktop (220–532 ms).
- **Run in Colab (author, 2026-10-13):**
  - the base built on Google Drive has 5,757 municipalities, A1 = 56,104,503 and B1 = 53,879,538, exactly the
    official totals;
  - the dry-run projection with everything counted is **51.01149%**, equal to the official two-party share.

  The independent system is ready for 25 Oct.
- **Live-loop test in Colab (author, 2026-10-13):**
  - first cycle, with all 5,757 municipal files: 53 s, against 228 s on the desktop;
  - later cycles took 0.4–2.2 s, every 30 s;
  - the media card was saved to Drive automatically (`card_e6257_0713.png`).

### P6 · 2026-10-12 · the 2022 governor run-offs as extra backtests: hypothesis refuted (`reports/p6_runoff_benchmark/`)
- **Idea:** the 12 governor run-offs of 2022 (AL, AM, BA, ES, MS, PB, PE, RO, RS, SC, SE, SP) could serve as extra
  run-off backtests for choosing the model.
  - Grid: 30 configurations of transfer weight, k_mun and min_frac_corr.
  - Selection: leave-one-state-out.
  - Held-out tests: the 2022 presidential run-off and 2022 r1 → 2026 r1.
- **Result: governor run-offs are not a valid proxy for the presidential run-off.**
  - Errors: mean of about 2 pp, maximum 13–18 pp.
  - Causes:
    - SE: the round-1 leader's votes were annulled *sub judice*, so the round-1 base does not reflect the run-off
      contest;
    - RO and AM: 2% of a small state is a few dozen sections in a handful of municipalities;
    - in general, state politics realigns between the rounds.
  - The leave-one-state-out error is 3.9 pp mean at 2%.
- **Held-out presidential tests:** the pre-registered draft (mean of transfer and swing) and the best governor config
  (transfer only) each have worst-case errors of about 0.6–0.8 pp. Neither reliably meets ≤ 0.5 pp at every
  checkpoint.
- **Decision:** keep the pre-registered draft model and its ±0.7 pp interval; nothing was tuned on the presidential
  tests.
- **Coverage (owner's idea: geographic representativeness rather than % counted):** in both presidential tests,
  `strata_covered` (lean × size strata with ≥ 1% counted) reached 1.0 at 5% counted, about 17:25 in the 2022
  run-off. Coverage could not be calibrated on the governor run-offs, for the reasons above.
- **Polling interval set to 30 s,** because round 2 is fast: 2% at 17:17, 50% at 18:26 and 99% by about 20:00 in
  2022.

### P1 · 2026-10-11 · backtest on 2022 round 2 (`reports/backtest_2022_t2_20261011-143556`, v0.3-dev)
- **Setup:**
  - round-2 sections in real TSE arrival order; 472,028 sections, 100% matched to round 1;
  - the model is a bounded transfer matrix, partially pooled UF → region → Brazil, with a municipal correction
    (`tally/project.py`), and 50 bootstraps per checkpoint;
  - the final result to predict is Bolsonaro 49.098%.

| % counted | Time (BRT) | UFs | Raw partial | Uniform swing | **Model** | Model 90% interval | Covered |
|---:|---|---:|---:|---:|---:|---|---|
| 0.5 | 17:09 | 22 | +6.03 | −0.49 | **+0.255** | 49.17–49.62 | no |
| 1 | 17:13 | 26 | +7.33 | −0.58 | **+0.017** | 48.90–49.33 | yes |
| 2 | 17:18 | 27 | +7.02 | −0.52 | **−0.080** | 48.85–49.14 | yes |
| 3 | 17:20 | 27 | +5.65 | −0.43 | **−0.078** | 48.95–49.20 | yes |
| 5 | 17:25 | 28 | +4.27 | −0.27 | **−0.085** | 48.95–49.07 | no |
| 10 | 17:33 | 28 | +2.91 | −0.12 | **−0.146** | 48.89–48.99 | no |
| 20 | 17:48 | 28 | +2.46 | −0.03 | **−0.103** | 48.91–49.04 | no |
| 50 | 18:26 | 28 | +1.21 | +0.01 | **−0.015** | 49.01–49.18 | yes |

(errors in percentage points of Bolsonaro's share of valid votes)

- **Accuracy:** from 1% of sections counted (17:13 BRT) the model's error is at most 0.15 pp. The raw partial count
  is off by 3 to 7 pp, and a naive uniform swing by about 0.5 pp.
- **Transfer of the others vote (Tebet, Ciro and the rest, about 7%):**
  - estimated at 2%: 48% to Bolsonaro and 35% to Lula;
  - with all data: 49% and 32%.

  The 2% estimate is already within 3 pp of the full-data value. Blank/null transfer is noisy early (0.54 at 2%
  against 0.26), but the group is small.
- **Ecological caveat:** the regression gives **net** flows. A1→A = 1.00 and B1→B = 0.98 sit on the bound, so
  offsetting gross switches (A→B and B→A) are invisible. The total is unaffected.
- **Intervals are too narrow:** 4 of 8 covered, against a nominal 90%. The bootstrap captures sampling error among
  counted sections, not the systematic error of extrapolating to regions not yet seen (about 0.1 to 0.25 pp here).
  Before round 2, a systematic term calibrated on this backtest must be added and pre-registered. One backtest is
  thin evidence for calibration.
- **Runtime:** about 3.5 min per checkpoint with 50 bootstraps on this desktop. That is too slow for live use, so the
  bootstrap must be made faster or run less often.

### P2 · 2026-10-11 · backtest with only municipal information (`reports/backtest_2022_t2_municipal_20261011-145419`)
The model is restricted to what is certainly live: per-municipality votes plus the number of sections counted.
Unlike the section model it does not know which sections.

| % counted | Section model (P1) | Municipal, naive | **Municipal, final config** |
|---:|---:|---:|---:|
| 0.5 | +0.255 | +0.801 | +0.621 |
| 1 | +0.017 | −0.188 | **−0.004** |
| 2 | −0.080 | −0.546 | **−0.133** |
| 3 | −0.078 | −0.649 | **−0.146** |
| 5 | −0.085 | −0.408 | **−0.051** |
| 10 | −0.146 | −0.285 | **−0.087** |
| 20 | −0.103 | +0.133 | **+0.051** |
| 50 | −0.015 | +0.484 | +0.309 |

The final configuration adds two things:
- a weak, candidate-symmetric prior on the national transfer matrix (500 pseudo-municipalities; loyalty 0.97;
  minor-candidate vote 0.40 to each side; blank 0.15; abstention 0.03);
- a municipal correction applied only to municipalities at least 50% counted.

**What the test showed:**
- **Why the naive version fails:** municipal aggregates are few and similar early on, so the transfer matrix is
  poorly identified, and partial big cities break the proportional approximation. In a synthetic worst case the
  naive version erred by 6.1 pp; the prior brings it to 1.0 pp.
- **Refuted hypothesis:** using round-1 arrival order to guess which sections of a municipality are counted made
  things worse (up to −1.1 pp). The arrival order does not repeat enough between rounds.
- **Big caveat, in-sample tuning:** the prior weight and the 50% threshold were chosen on this same 2022 backtest.
- **The prior dominates:** with this weight, the estimated transfer of the others vote stays at about 0.46 to A and
  0.37 to B at every checkpoint, close to the prior. It happens to be near the full-data 2022 value (0.49 and 0.32),
  but in 2026 a lopsided transfer would be under-detected.
- **Before trusting this mode:**
  - validate it out of sample, for example on the 2018 run-off (Bolsonaro × Haddad);
  - lower the prior weight as data accumulate.

### P3 · 2026-10-11 · out-of-sample check on real 2026 data (`reports/cross_2022t1_to_2026t1_20261011-145808`)
- **Scope decision (owner):** only 2022, as the model year, and 2026 are used; 2018 is excluded because its system
  is too different. The out-of-sample check is therefore the 2026 round-1 count, replayed in real arrival order and
  projected from the 2022 round-1 sections.
- **Setup:**
  - 92.39% of 2026 sections match a 2022 section key;
  - the metric is Flávio's share of Flávio + Lula, whose final value is 51.011%;
  - the municipal configuration is the one frozen in P2.

| % counted | Raw partial | **Section model** | Municipal, P2 config | Municipal, naive |
|---:|---:|---:|---:|---:|
| 0.5 | −1.19 | −0.112 | −1.706 | −0.714 |
| 1 | +1.89 | −0.214 | −1.406 | −0.952 |
| 2 | +3.02 | **−0.034** | −0.979 | −0.528 |
| 3 | +3.47 | +0.070 | −0.823 | −0.383 |
| 5 | +3.93 | +0.128 | −0.646 | −0.308 |
| 10 | +4.50 | +0.144 | −0.647 | +0.118 |
| 20 | +4.61 | +0.130 | −0.241 | +0.449 |
| 50 | +3.56 | +0.124 | −0.189 | +0.134 |

- **The section model generalises:** its error is at most 0.21 pp, and −0.03 pp at 2%, on data it never saw.
- **The municipal model does not:** the P2 prior, tuned on the 2022 run-off, makes it worse out of sample (−0.98 pp
  at 2%). This confirms the P2 warning that the municipal mode is prior-dominated and fragile.
- **Conclusion:** projection accuracy depends on knowing **which** sections are counted. For round 2:
  1. the priority is to obtain section identity live, from `cs.json` and `aux` if they update during the count;
  2. the municipal mode is only a fallback. It should run without the tuned prior (naive or a weak prior) and be
     presented with wide intervals (±1 pp).
- **Open question:** whether section identity is available live. The simulation environment
  `resultados-sim.tse.jus.br` is online, but its JSON paths returned 403. P4 shows that identity alone would not
  remove the municipal-level limit anyway. *(Edited 2026-10-11: an inference about a third party's data source was
  removed.)*

### P4 · 2026-10-11 · the limit of municipal-level live data (cross backtests 2022r1→2026r1 and 2022r1→2022r2)
The goal was to measure how accurate a projection can be when votes arrive only as municipal totals, which is
what TSE publishes live. Error in pp of A/(A+B):

| % counted | Section votes (P1) | Transfer, naive | Transfer, sections identified | Swing, proportional | Swing, sections identified |
|---|---|---|---|---|---|
| 2026 r1, 2% | −0.03 | −0.53 | −1.12 | −0.42 | −0.74 |
| 2026 r1, 5% | +0.13 | −0.31 | −0.96 | +0.27 | −0.50 |
| 2022 r2, 2% | −0.08 | −0.55 | −0.10 | −0.67 | −0.13 |
| 2022 r2, 5% | −0.09 | −0.41 | −0.31 | +0.12 | −0.19 |

- **Precision needs section votes.** Errors of about 0.1 pp come only with **section-level votes**. With municipal
  totals, every method lands at about 0.2 to 1.0 pp, and their sign and ranking change between the two elections.
- **Identity is not the bottleneck.** Knowing *which* sections are counted, while votes stay municipal, does not
  reliably help. The binding constraint is the aggregation of the votes.
- **Realistic expectation for 25/10:**
  - with municipal data, A/(A+B) is about ±0.5 pp at 2–5% counted, i.e. about ±1 pp on the margin;
  - an early call is credible only if the margin is clearly larger than that;
  - the round-1 live projection publicly reported by Rodrigo Mahlmeister (NeoFeed, October 2026: Flávio within
    0.02 pp, Lula off by 0.34 pp, so about 0.36 pp on the margin) is consistent with this range.

### P5 · 2026-10-11 · the round-2 projection rule (input to PREREGISTRATION_ROUND2_PROJECTION.md)
- **Estimate:** the mean of the transfer model without prior and the municipal swing model. Neither has tuned
  parameters.
- **Errors of this mean (pp):**

| Backtest | 2% | 3% | 5% | 10% | 20% | 50% |
|---|---|---|---|---|---|---|
| 2022 r1 → 2026 r1 | −0.474 | −0.160 | −0.022 | +0.370 | +0.625 | +0.253 |
| 2022 r1 → 2022 r2 | −0.609 | −0.549 | −0.142 | +0.034 | +0.299 | +0.502 |

- **Envelope:** max |error| is 0.625 pp, so the pre-registered half-width is ±0.7 pp. Errors are not monotone in the
  share counted, because partially counted big cities keep the proportional proxy biased.
- **Live = backtest:** `tests/test_live_projection.py` shows the live path gives exactly the backtest value.
- **End-to-end dry run** on the round-1 files: `tally live --election 6257 --once --project` printed the projection
  line correctly.

<!-- phase2:end -->
