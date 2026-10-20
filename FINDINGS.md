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

### Overall conclusion of the 2026 round-1 analysis
1. The published national result is exactly the sum of the 499,206 public section BUs.
2. Sections received during the freeze, during the slowdown, right after the gap and in the tail are statistically
   indistinguishable from sections in the same polling location received at other times.
3. There **was** a real, nationwide 27.5-minute pause in TSE's reception records. It is an operational event that
   deserves an official explanation, and the data show no trace of it in the votes.
4. **What this does not cover** (METHODOLOGY §6): manipulation inside the ballot box applied uniformly, which no
   section-level statistic can see.

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

