
## 2026-10-27 — integrity-test idea (author): paths 3 and 1
- Source: Res. TSE 23.673 (compiled text). Art. 66-J (Res. 23.758/2026) bars supplying BU image, RDV and logs of
  tested boxes, so no labelled "simulated voting" logs exist for us.
- **Path 3 (E10, `exploratory/e10_load_dates_2026r2.py`):** list every load (SCUE) and boot (GAP) block of every
  raw log: date, mode, section. Aim: find the substitute boxes of sections drawn for the test (prepared on the eve,
  art. 62) and compare with the TRE lists. Structural fields only (like S7), so it runs on both halves; no voter
  trail is read in C.
  - Seen on one RR log: the box was loaded once (SCUE, 22/09) and moved to round 2 by GAP on 15/10 ("Urna
    transitada para 2º turno"), with no new load.
- **Path 1 (E11, `exploratory/e11_scripted_trails.py`):** scripted trails from the rule text (one typist, random
  order, 83–95% of the electorate, stop at 17:00, no fingerprint). Use: power of the frozen S1–S6 against k
  fingerprint-free votes injected into real D boxes (spread, block, end of day). Smoke test: 50 whole scripted boxes,
  S3 flags 0. Power study waits for the D trails.

### 2026-10-27 ~07:10Z — E10 first run (234,089 logs: H7r2 raw + second pass so far; UFs AC–PA complete)
- Last successful load (SCUE "Urna carregada com sucesso") by date: the bulk 18/09–01/10; **387 boxes loaded on
  24/10** (eve of round 2); 933 boxes booted on 25/10 in mode "Urna de contingência".
- **Check against TRE-MG's published list** (33 integrity-test sections, round 2, incl. 3 biometric): 34 MG boxes
  loaded on 24/10; 31 of them are in the list. The 2 listed sections not caught had a box loaded in September with
  no round-1 votes (a reserve box). The 3 eve loads not in the list: MG 159/71, 184/163, 270/175 (other replacements,
  to check). Several complete UFs show exactly 20 eve loads (AL, AM, AP, DF, ES, MS); TRE-ES announced 18.
- So the substitute boxes of tested sections are visible in public logs. Use: an exclusion/flag list
  (`tested_r2`), and a check that the TRE lists match what the logs show.
- **New lead (structural):** 2,943 boxes have a load dated before the generation date of their own load media,
  so the box clock was wrong at load (the load asks the operator to type date and time). Concentrated: CE 1,356,
  RJ 755, BA 241. Some loads are dated 1970, 2009, 2023–2025 or 2027–2035. To check whether these boxes differ in
  anything else (model, version, round-2 timing).

### 2026-10-27 — second pass complete; the 4 SE round-1 cases are round-1 integrity-test boxes (D)
- E9 second pass finished: 464,203 logs fetched, 0 failed, all SHA-256 checked. E10 rerun on every log started.
- The 4 SE sections left unexplained by E8 (log box differs from the bweb box and appears in no round-1 bweb row:
  31690/12/87, 31712/13/82, 31755/5/143, 32514/35/57). Fetched their **round-1** logs (pleito 3220; stored under
  `data/urna_logs/p3220_cases/`, not versioned):
  - the round-1 log holds only the bweb box, whose first event is on **03/10** (eve of round 1), with the bweb vote
    count and close time;
  - the round-2 log's box was loaded in September for the same section, booted on 04/10 at ~07:15, ran 08:00–17:00
    as that section and printed its own BU (164, 189, 180, 202 votes against 169, 192, 174, 262 in bweb).
  - Reading: the original box went to the round-1 integrity test, a substitute loaded on the eve ran the real
    election, and the original box came back for round 2 (art. 62). E8's 17 unexplained cases fall to 13.
- **The test trails are visible** (round-1 events kept in the round-2 log; art. 66-J bars TSE from supplying
  them, but they come with the box's next log). Test box vs the real box of the same section, round 1:

| Section | n test / real | manual enabling test / real | mean fingerprint attempts | median booth time (s) |
|---|---|---|---|---|
| 31690/12/87 | 164 / 169 | 0.99 / 0.06 | 3.96 / 1.63 | 38 / 72 |
| 31712/13/82 | 189 / 192 | 0.98 / 0.04 | 3.92 / 1.46 | 28 / 54 |
| 31755/5/143 | 180 / 174 | 0.99 / 0.05 | 3.97 / 1.45 | 26 / 61 |
| 32514/35/57 | 202 / 262 | 0.99 / 0.05 | 3.98 / 1.34 | 35 / 57 |

  - Telemetry of simulated voting: every voter fails all 4 fingerprint attempts and is enabled manually ("Dado
    digitado confere"); booth time is about half; the operator runs "Inspeção da urna" through the day.
  - Test ballots are 62–82% of QT_APTOS here, below the 83–95% in art. 63 (the share may be of a different base;
    not followed).
- **Uses:**
  1. A real positive control for path 1: S2 (manual enablings, longest run) should flag these round-1 trails; E11
     injections can be calibrated on them (typing speed, booth time).
  2. A scan for other reused round-1 test boxes: round-1 trails with manual share near 1 and ~4 attempts per voter
     in round-2 logs. These boxes must be excluded from the round-1 control of S2/S5 (they are covered by the
     "changed box between rounds" exclusion, since the bweb round-1 box differs).
  3. For round 2, the same pattern is what a fingerprint-free injected vote looks like; biometric enabling cannot
     be faked without fingerprints, so S2 is the detector that matters for that kind of insertion.

### 2026-10-27 — national scan for reused round-1 test boxes (rule fixed before running)
- Source: the H7r2 per-log summary (round-1 `votes`, `biometric`, `manual`, `urn_ids`), already computed for every
  log in both halves. No voter trail is read and no round-2 field is used, so the scan runs on D and C alike; it
  produces an exclusion list for the round-1 control, not a round-2 signature.
- Rule (fixed before looking): a log is a **round-1 test box** if its round-1 votes >= 50 and manual / (manual +
  biometric) >= 0.90. Reported alongside: the share band 0.50–0.90 (to see if the cut is clean) and, per hit, whether
  the box matches the round-1 bweb box (E8).
- **Result of the fixed rule: it failed its own control.** It caught 2 of the 4 known SE test boxes. The H7r2
  summary's `manual` counts "Mesário … habilitou o eleitor" (poll-worker authorisation), which two test boxes do
  not have. The 28 hits are mostly totalised boxes (bweb box matches) with poll-worker-authorised enablings: a
  biometric-trouble pattern, not a test (e.g. BA 36854/180, four sections). Kept in `r1_test_box_scan.csv`; not
  followed further here.
- **What separates a test box is that it was not totalised.** Second scan, on the H7r2 summary plus a new counter
  of round-1 event types (`exploratory/e13_r1_enabling_counts.py`: votes, biometric, manual request, "Dado digitado
  confere", poll-worker authorisation, "Digital coletada bate com uma digital gravada após o registro", inspection;
  counts only):
  - logs whose round-1 box appears in no round-1 bweb row: **5 in the whole country, all SE**;
  - all 5 have the test profile (manual requests 94–99% of votes, poll-worker authorisation 0–162, the "same finger"
    message up to 199): the 4 above and **SE 32476/23/118**, which E8 had counted as "replaced";
  - among E8's 2,021 replaced/unexplained cases, no other log has a manual share >= 0.9, except one.
- **New lead (C half, counts only, trail not read): RJ 60011/8/74, round 1.** A replacement box (ready 16:16, open
  until 19:16, 66 votes; bweb box and count consistent). 62 of 66 voters had a manual request, 55 had the "same
  finger" message, no poll-worker authorisation. To know whether this is rare, a full E13 pass over every log is
  running (event counts only, round 1). Ordinary explanations to check first: how the replacement box handles
  biometrics, and what the "same finger" message means (it also appears 17 times in a normal BA box).
- Exclusion list for the round-1 control of S2/S5: the 5 SE logs (`r1_test_box_scan.csv`, `unknown_box` true).

### 2026-10-27 ~10:50Z — E10 complete (499,176 logs, all UFs)
- **Eve loads (last load on 24/10): 756**, every one with round-2 votes. By UF: most have exactly 20 (AL, AM, AP,
  DF, ES, MS, RR, SE), others 16–40, SP 116, ZZ 0. Listed in `tested_r2_candidates.csv`: the candidate set of
  round-2 integrity-test substitutes (plus ordinary eve replacements; MG showed 31 of 34 in the TRE list). To check
  against the TRE lists as they are published.
- Boots on 25/10 in "Urna de contingência": 1,975.
- **Clock lead, downgraded.** 7,990 boxes have a load dated before their own load-media generation date. Most of
  the wrong dates are a few days to weeks early in 2026 (Sep 5,378, Aug 1,336, Jul 1,153); odd years are rare
  (2009: 23, 2025: 23, 2024: 14, 1970: 4). They cluster by zone: 744 of 2,641 zones have any, and 47.5% of the
  boxes sit in zones where at least half the boxes are affected (RJ 75, 76, 98, 245; CE 37, 123: 96–100%). A
  zone-wide pattern points to a load-site procedure (one clock setting per zone), not to anything per box or per
  voter. Not followed further unless these zones stand out in S1–S7.

### 2026-10-27 — clock lead withdrawn: extractor artefact (correction of the two entries above)
- E10 dated each load block by its first line ("Iniciando aplicação"), which carries the box's internal clock
  **before** the operator sets it. The load sequence is: "Data e hora solicitadas" → "Data e hora que foi digitada
  pelo operador: <date>" → "Data e hora atualizada" → media check → "Urna carregada com sucesso", all after the
  clock is set. Example (RJ 58190/75/7): internal clock 08/09, typed 24/09, media generated 19/09, load done 24/09.
  An abroad box started at 01/01/2009 (the default after a clock reset) and was set to 17/09.
- Check on a random 400 of the 7,990 flagged boxes: in **400 of 400** the typed date and the "Urna carregada com
  sucesso" date are on or after the media generation date. No load happened before its media existed, and no
  operator typed a wrong date in the sample.
- What remains is that about 8,000 boxes had an internal clock running behind (or reset) when taken out of storage,
  which the load procedure corrects by design. Clustering by zone fits boxes stored together. Not a lead.
- Earlier statements in this log and in chat ("box clock wrong at load", "typing error", the 2,943 / 7,990 counts)
  are withdrawn. E10's per-block `date` is the pre-set internal clock for SCUE blocks; any use of it must take the
  date of "Urna carregada com sucesso" instead. The eve-load count (756) can only be an undercount (a box whose internal clock lagged on 24/10 would be dated earlier); the clocks were
  already set, and the MG check matched 31 of 34.

### 2026-10-27 — RJ 60011/8/74 (round 1, C half, event counts only; trail not read)
- Meaning of "Digital coletada bate com uma digital gravada após o registro inicial de mesário" (read on a D box,
  BA 36854/180/202): after a manual enabling the box asks for a poll worker's finger; it is compared with each
  poll worker registered at opening ("Biometria coletada não é do mesário …" for each), and the message says it
  matches a finger recorded later that day instead. So the authoriser is not one of the registered poll workers,
  and is the same finger each time.
- The RJ box: booted at 16:05 as "Urna de contingência", then loaded with section 74's voting media; model UE2013
  (485.8 MB memory); 4 poll workers registered; 66 votes; the reader captured a finger in every attempt (62/62/61/60
  captures, 384 scores), 62 voters failed all 4 attempts and were enabled manually; each authorisation failed
  against the 4 registered poll workers (240 messages) and matched a later-recorded finger (55).
- Against all 2,004 replacement boxes (`replaced_r1_models.csv`, round-1 manual share by model, boxes with >= 20
  votes): UE2013 median 0.086, p90 0.16, max 0.939 (this box; next 0.45, BA 38890/128/144); UE2015 max 0.22;
  UE2020 max 0.30; UE2022 max 0.94 (SE 32476/23/118, the test box). **The old model does not explain it: 1 of 576
  UE2013 replacement boxes.**
- Reading so far: captures in this box match each other (the authoriser's finger matches its own earlier capture)
  but match neither the voters' enrolled templates nor the poll workers registered minutes before. That fits a
  single miscalibrated or defective sensor. It also fits a person other than the registered poll workers enabling
  62 voters. The log alone does not separate the two.
- What would separate them:
  (a) the same box's round-2 behaviour (if the log's round-2 part shows the same failure for the same section's
      voters, the sensor explanation holds). This is a round-2 field in C: it needs a sealed rule (§0) before it is
      read;
  (b) the section's minutes (ata) for 04/10 and the poll workers' account; (c) a physical check of the box.
- Status: **open lead, unexplained pattern, one section.**

### 2026-10-27 — sealed test C-01 run once (RJ 60011/8/74): device explanation supported
- Sealed in `commitments/c_test_01_rj_60011_8_74.md` (SHA-256 184fe45b…, OpenTimestamps submitted to 4 calendars,
  commit 9991d5f) before any round-2 field of the section was read.
- Applicability: same box id in both rounds (01671293), round 2 booted in normal "Votação" mode.
- Result: 25/10, 300 votes (08:01–16:49), manual requests 270, biometric 3: **m2 = 0.90 ≥ 0.50 → device explanation
  supported.** The same box failed to match the same section's voters in round 2 as in round 1.
- Descriptive (not part of the rule): in round 2 the authorisations matched the poll workers registered in the box
  (269 "habilitou o eleitor", 579 non-matches while cycling through them, 0 "later-recorded finger"). So the box
  matches fingers captured on its own sensor and fails against enrolled templates captured elsewhere, which is what a
  miscalibrated sensor would do. The round-1 non-match of the registered poll workers stays unexplained in detail,
  but the "other person" reading has nothing left to rest on.
- **Lead closed: equipment fault** (to confirm with the minutes if they become available). For the detectors: this
  box enables ~90% of voters manually in both rounds; S2(a) compares round 2 with round 1 of the same box, so it
  should not flag it, and S2(b) round-2 runs will be long. Listed as a known device case.

### 2026-10-27 ~13:00Z — E13 complete (round-1 event counts, every log)
- 494,371 logs with round-1 votes. Manual-request share per box: median 0.064, p99 0.199, p99.9 0.291. The
  "later-recorded finger" message appears in 49% of boxes (median share 0, p99 0.11).
- Boxes with >= 50 votes and manual share >= 0.5: **85**. Not in bweb: **5, the SE test boxes** (no other reused
  round-1 test box in the country). The other 80 were totalised. By half: D 66 (BA 29), C 19. They cluster by zone
  (BA 38830/162, 36854/180, 39330/128, 39136/33; PE 23817/105; PR 79294/19). Model: 54 of the 68 D cases are UE2013.
  List: `r1_enabling_outliers.csv` (also boxes with "later-recorded finger" share >= 0.3).
- **Round 2 of the same box, D half only** (`r1_enabling_outliers_D_r2.csv`): all 68 kept their box. Manual share
  in round 2 >= 0.5 in 46 (the device keeps failing, as in C-01), 0.2–0.5 in 10, < 0.2 in 12.
- The 12 that recovered, round-1 trail by hour:
  - abrupt switch within the day (manual ~1.0, then ~0.1 from a given hour on): BA 30872/186/10 (13h), BA
    38830/162/46 (first 136 voters manual, then biometric), PR 75191/79/1 (14h), BA 36854/180/445 (18h), PE
    23817/106/278 (15h), PR 76759/102/58 (17h), RS 88633/47/16 (a 12–15h failure window). A reader failing and
    being fixed (or reconnected) during the day.
  - BA 37656/94/115 and MA 9474/50/104: the trail shows biometric enabling for almost all voters although the box
    logged more manual-request messages than votes. The manual-request message is not the same as a manual
    enabling; E13's `manual_ask` overstates in such boxes. The trail (`bio`) is the measure to use.
  - steady all day, normal in round 2: BA 38830/162/153 (0.94 → 0.07; three other boxes of the same zone are also
    outliers, two of them still failing in round 2), RS 88188/81/293 (0.3–0.6 → 0.16). Consistent with a reader
    swapped or serviced between rounds; nothing in the counts separates that from other readings.
- Reading: the round-1 high-manual boxes are an equipment pattern (old model, zone clusters, failure windows,
  persistence in the same box). No signature found here. Open, low priority: BA 38830/162/153 and RS 88188/81/293.

## 2026-10-27 — E12 complete (per-voter trails, every log)
- `exploratory/e12_trails_2026r2.py --procs 6`, about 2 h 35 min (file times 13:00 → 15:35, machine clock): 499,176 logs, 28 UFs,
  **0 unreadable**. Output in `D:/tally-forensics-data/trails/` (2.5 GB; per UF `_r1`, `_r2`, `_boxes` parquet).
- 128,077,499 round-2 voter trails ("O voto do eleitor foi computado"). Not yet compared with the round-2 bweb
  turnout (not published); that comparison is part of H7r2.
- Next: S7 and S1–S6 on both halves, with the listed exclusions (5 SE round-1 test boxes, changed/replaced boxes,
  known device cases), then the E11 power study on D.

## 2026-10-27 — S7 (software) on both halves: 3,571 logs listed, all with an ordinary explanation
- `exploratory/e14_s7_software.py` → `reports/h8r2/s7_software.csv`. 499,176 logs; one application version in every
  box (10.23.0.0 "Praia da Barra do Cahy"). Listed: 3,571 (D 757, C 2,814). Every listed log was opened (structural
  lines only: version, signature checks, power events; allowed on C by the S7 rule).
- **2,261 — "second version" = UEFI line.** The frozen `software()` takes every line starting "Vers", so a box that
  also logs "Versão do UEFI: IYEA24_P" (UE2020) or "IYEA26_P" (UE2022) gets a composite version string. One UEFI
  string per model; 0.4–0.7% of UE2020/UE2022 boxes print it (PI 3.1%, the highest). Parser effect, not a
  software difference. Recorded as a known imprecision of the frozen code; no code change.
- **1,281 — all of ZZ (abroad).** Abroad media carry `o#####zz-pu.vsc` instead of `o#####br-pu.vsc`; the frozen
  normalisation maps the first to "uf" and keeps "br". Same file role. Explains the C excess.
- **5 — no external-media section file** (`-lo.vsc` missing from the check list): ES 57932/9/85, 57932/9/112,
  RJ 58696/27/139, SP 61654/14/250, SP 64777/393/312. All have 0 round-2 votes (boxes not used on 25/10).
- **24 — one signature check reported ERRO** (D 13, C 11), always in GAP, one file each (voice files, `avlib`,
  `avboot`, `avusr*`, `infomidia.vsc`, one section `-lo.vsc`). In every case: exception "ValidaAssinaturas …
  9336", box switched off, and the same file checked SUCESSO at the next full validation, 2–13 minutes later, in
  23 of 24. PR 78859/8/278: ERRO on the external-media `-lo.vsc` on 17/10 09:38; the boots that followed that day
  checked only the internal copy; the next full check (24/10 08:36) and the round-2 morning check (25/10 07:14)
  were SUCESSO. Pattern of a transient read error; none blocks the round-2 day.
- Reading: S7 finds no box with a different application or file set. No signature found so far.

## 2026-10-27 — S1–S6 on both halves (E15): decision table
- `exploratory/e15_s1_s6.py` → `reports/h8r2/s1_s6/` (decision.csv, flagged.csv, exclusions.csv, per-detector
  parquet, s4_blocks.csv, s6.json). Run log `reports/h8r2/e15_run.log`.
- Implementation: per-box detectors run on 101 chunks of boxes; Bonferroni recomputed over each half with the frozen
  `bonferroni_flags`. S4 (cross-box) and S5 (national deciles) use chunkable copies of the frozen code; both were
  checked identical to the frozen functions on whole AC and RR, S4 also on a positive case (one 10-voter block
  copied into another box). S1 group labels built as in `ballot_group` (shared strings, for memory).
- Exclusions (`exclusions.csv`): 16,141 logs of sections with aggregated sections (round-1 bweb flag; round-2 file
  not out), all detectors; the 5 SE round-1 integrity-test sections, round-1 tables only; S2/S5 pairing requires the
  section's only log, round-1 log votes = round-1 bweb turnout, and no E8 case: 476,429 paired, 6,601 not.
  Known device cases marked, not excluded. ZZ has no municipal time-zone offset and is outside S6 (agreed with the
  author 2026-10-27).
- National round-1 score deciles: 5, 10, 32, 50, 68, 86, 107, 132, 167.

| half | det | flagged r2 | control | rule met |
|---|---|---|---|---|
| D | S1 | 414 | 1,210 (r1) | no |
| D | S2a / S2b | 14 / 17 | 21 / 41 | no |
| D | S3 | 17 | 38 | no |
| D | S4 | 0 boxes | 0 | no |
| D | **S5** | **1,178** | **0** | **yes** |
| D | S6 | 0 spikes | 0 | no |
| C | S1 | 635 | 2,459 | no |
| C | S2a / S2b | 12 / 13 | 10 / 21 | no |
| C | S3 | 28 | 13 | no (ratio met; Holm p 0.083) |
| C | S4 | 0 boxes | 0 | no |
| C | **S5** | **1,100** | **0** | **yes** |
| C | S6 | 0 spikes | 0 | no |

- **S5 meets the §3 rule in both halves. Hunt on D (C not opened beyond the fixed detector):**
  - In the raw trail, "Batimento de digitais retornou o score" comes after "Solicita digital do mesário", followed
    by "Biometria coletada não é do mesário …" / "Mesário … habilitou o eleitor". **The score is the poll worker's
    fingerprint matched against the registered poll workers, not the voter's.** The voter's own attempts log no
    score. Every scored trail is a manual enabling (bio = 0): 6.3% of voters in round 1, 6.5% in round 2.
  - So S5 compares the poll workers who authorise manual enablings in each round. A change of who authorises (a
    different person, finger or registration order) changes the box's score mix; the round-1 even/odd control keeps
    the same workers on both sides and cannot see that. The control is not a valid null for a between-round change.
  - Data agree: flagged boxes move both ways (median score up in 58%, down in 42%); their share of non-match scores
    (≤ 12) changes by 0.30 on average against 0.08 in unflagged boxes; mean comparisons per scored voter (number of
    registered workers tried) fall by 1.07 against 0.19. All four models and all 13 UFs are affected (flag rate
    1.1–3.9% by UF, 2.3–5.5% by model). Worker identity cannot be compared across rounds: the per-box index is
    rebuilt each day and the numbers are not stored (personal data).
  - **Reading: S5 as frozen measures poll-worker turnover, not voter trails. Protocol defect, recorded here; the
    S5 result is reported and not counted as a signature.** No signature found so far. A sealed C test of the
    explanation (direction balance and non-match-share change in C's flagged boxes) is proposed, not run.
- **S6 has no power as frozen.** Spike threshold = Poisson isf(1e-6, λ) + 1 = 6–10 votes in one minute for real
  rates (λ 0.2–1.0/min). A box never casts more than 3 votes in a minute (SE round 2: 1,176,149 box-minutes with 1,
  143,359 with 2, 264 with 3). The synthetic test used 8 votes in a minute, which a real box cannot produce. The
  zero result says nothing about synchrony. Recorded for the E11 power study; any new form goes through a sealed
  deviation.
- S1, S2, S3, S4: no excess over control in either half. S1 and S2 flag fewer boxes in round 2 than in round 1.

### 2026-10-27 — sealed test C-02 run once (S5 flags in half C): P1 fails, lead opened
- Sealed in `commitments/c_test_02_s5_poll_worker_scores.md` + `exploratory/e16_c02_s5_turnover.py` (SHA-256 and
  OTS, commit 6a2c648). Dry run of the same code on half D before sealing reproduced the D benchmarks exactly.
- Result (`reports/h8r2/c_test_02_result.json`): 49,730 C boxes tested, 1,100 flagged.
  - P1: median score up in **0.671** of flagged boxes; sealed band [0.35, 0.65] → **fails**.
  - P2: mean |change in non-match share| 0.373 flagged vs 0.090 unflagged → holds.
  - P3: scored round-2 trails manual 1.000 → holds (the score is the poll worker's in C too).
- **Decision as sealed: a change common to C boxes that the explanation did not predict; the flagged C boxes are a
  lead.** List: `reports/h8r2/s1_s6/flagged.csv`, detector `S5:flag`, half C.
- Follow-up on D (E17, `exploratory/e17_poll_worker_counts_D.py` → `poll_worker_counts_D.parquet`; event counts
  only, no numbers): poll workers registered per box 7.34 (r1) vs 7.51 (r2); non-match comparisons per authorisation
  request 2.112 vs 2.015 nationally in D. Flagged D boxes with the median up have non-matches per request down by
  0.51 (down-boxes 0.12); the number registered does not separate them (up share 0.58–0.61 for fewer, equal or more
  registered). Reading: in round 2 the authorising poll worker tends to be found earlier in the comparison list, so
  fewer non-match scores precede the match. That is consistent with an ordinary change of who authorises or of the
  registration order, but the comparison order cannot be checked without poll-worker identities (personal data, not
  stored) or the section minutes.
- What the lead concerns: the authentication of the poll worker who authorises a manual enabling. It does not touch
  the voter trail or the count; S2a (manual enablings, round 2 vs round 1) shows no excess in either half.
- Status: **open lead, no signature found so far.** Next ordinary check: the minutes of a sample of flagged sections
  (who served, registration order). Also noted: the [0.35, 0.65] band was set from D's 0.584; D sits inside it,
  C's lean is stronger.

## 2026-10-27 — E11 power study on D with a real positive control
- `exploratory/e11_power_D.py --hosts 1000` → `reports/h8r2/e11_power_D.csv`. Control: the 890 round-1 trails of the
  5 SE integrity-test boxes (manual 0.979, fingerprint attempts 3.92, enabled→computed median 35 s; normal boxes
  0.067, 1.52, 56 s). Injected into round 1 of 1,000 paired D boxes with ≥ 150 round-1 votes (same six-office
  ballot); flags at the Bonferroni n of the real E15 round-1 run of D. Seed 20261026.
- Share of hosts flagged:

| mode | k | S1 | S2a | S2b | S3 | any |
|---|---|---|---|---|---|---|
| none | 0 | 0.011 | 0 | 0 | 0 | 0.011 |
| block | 5 | 0.011 | 0 | 0 | 0 | 0.011 |
| block | 10 | 0.023 | 0 | 0.685 | 0 | 0.690 |
| block | 20 | 0.036 | 0 | 0.981 | 0.009 | 0.982 |
| block | 40 | 0.079 | 0.258 | 1.000 | 0.715 | 1.000 |
| block | 80 | 0.106 | 0.993 | 1.000 | 1.000 | 1.000 |
| spread | 10 | 0.013 | 0 | 0 | 0 | 0.013 |
| spread | 20 | 0.040 | 0 | 0 | 0.003 | 0.043 |
| spread | 40 | 0.072 | 0.268 | 0 | 0.474 | 0.602 |
| spread | 80 | 0.102 | 0.995 | 0 | 0.938 | 0.998 |

- Reading:
  - Consecutive typed votes are seen from about 10 per box (S2b, longest manual run).
  - Typed votes spread through the day are not seen below about 40 per box (15% of a 270-vote box); 20 per box
    pass in 96% of boxes. Summed over many boxes, that is a large undetectable volume for these detectors.
  - S1 (turbo) barely reacts: the control is faster than normal (35 s vs 56 s) but not at the 0.1% quantile.
  - This power is against trails like the control (manual, failed fingerprints). Trails that imitate biometric
    enabling would not move S2 or S3 at all; the log detectors cannot see them.
  - S1 flags 1.1% of hosts with nothing injected: real fast boxes exist in round 1 (E15: 1,210 round-1 flags in D),
    so S1 flags are leads, not evidence, as the protocol says.
- Consequence for reporting: "no signature found" by S1–S4 means no typed-vote pattern of ≥ ~10 consecutive or
  ≥ ~40 spread per box; it says nothing about smaller or biometric-like insertions. S6 as frozen has no power
  (E15 entry). Any redesign is a sealed deviation.

## 2026-10-27 — Deviation 01 (S6') sealed and run once; power on real D data
- Sealed: `commitments/deviation_01_s6prime.md` + `tally/s6prime.py`, `tests/test_s6prime.py`,
  `exploratory/e18_s6prime.py` (SHA-256 and OTS, commit 4fcb584). Before sealing, two end-of-day edge effects found
  on synthetic data were fixed (symmetric window; exposure = boxes in their interior); the synthetic tests then
  passed with no false alarm on 6 clean sets. Dry run of the runner on RR round 1 only (half D).
- Run once (`reports/h8r2/s6prime/`, log `reports/h8r2/e18_run.log`). Flagged bins:

| half | round 1 A / B1 / B2 | round 2 A / B1 / B2 |
|---|---|---|
| D | 0 / 17 / 11 | 0 / 0 / 0 |
| C | 0 / 23 / 14 | 0 / 0 / 0 |

- **Decision as sealed: no round-2 bin flagged in either half; no coincidence; no signature found so far.**
  Closest round-2 bin: C B2, p 5.7e-5 against a threshold of 3.2e-5 (not flagged).
- Round-1 control flags are one continuous block 16:42–17:05 BRT in both halves (B1/B2): the round-1 closing queue
  (six offices), a bump of more than 20 minutes, not a one- or two-minute trigger. The detector sees real
  time-of-day events.
- Power on real data (`exploratory/e19_s6prime_power_D.py` → `s6prime/power_D_r2.csv`; trigger injected into D round
  2, about 230,000 boxes; 10 random minutes 10:00–15:59 per N):

| statistic | trigger | detected at N boxes |
|---|---|---|
| A | 3 extra votes per box | 5: 0.0, 10: 0.2, 20: 0.5, **40: 1.0**, 80: 1.0 |
| B1 | 1 extra vote per box | 500–1,000: 0.0, 2,000: 0.2, **4,000: 1.0** |
| B2 | 1 extra vote per box | ≤ 2,000: 0.0, 4,000: 0.1, **8,000: 1.0** |

- Reading: a one-minute trigger is seen from about 40 boxes at 3 votes each, or about 4,000 boxes (1.7% of a half)
  at 1 vote each. A trigger spread over minutes, or below those sizes, is not seen.

## 2026-10-27 — S5 lead (C-02): minutes to request
- `exploratory/e20_s5_minutes_sample.py` → `reports/h8r2/s5_minutes_request.csv`: 30 of the 1,100 half-C sections
  flagged by S5 (seed 20261027) and, for each, an S5-tested unflagged control in the same zone with the nearest
  section number. Uses only the E15 flags and the box table; no new half-C field read.
- Flagged by UF: SP 8, SC 7, RJ 4, AL 3, MG 3, PI 3, AM 1, GO 1 (8 TREs).
- What is asked, per section and round, in anonymised form (no names or voter numbers): number of poll workers who
  served; for each role (president, 1st/2nd mesário, secretaries), whether the same person served in both rounds;
  substitutions during the day; occurrences about poll-worker biometrics, manual enabling or the reader.
- The comparison rule (flagged vs control) is to be sealed as C-03 before any minute is received.
- C-03 sealed (`commitments/c_test_03_s5_minutes.md`, script `exploratory/e21_c03_minutes.py`, template
  `data/minutes/s5_minutes_answers_template.csv`, sample CSV; SHA-256 and OTS) before any minute was requested.
  Outcomes: O1 turnover in any mesa role, O2 biometric/reader occurrence; paired one-sided exact McNemar, Holm,
  alpha 0.05, at least 15 complete pairs. Script checked on synthetic answers only (supported / not supported /
  too few pairs).

## 2026-10-28: sealed test C-04, round-2 collapse or zero for candidate A (author's question)
- Reports heard by the author: sections where Flavio Bolsonaro had very large round-1 votes and collapsed or got
  zero in round 2. The round-2 bweb is not out, but every section's `bu.dat` is on TSE's results site, in the
  same folder as the logs. `exploratory/e22_fetch_bu_r2.py` fetches all of them (30 rps, SHA-256 manifest on D:).
- Format check only: one Acre BU (half D) dumped, and the parser checked on RR (half D): for each section,
  22 + 13 + blank + null equals the log's round-2 vote count. No other round-2 vote count was read.
- Rule written and sealed before the run: `commitments/c_test_04_r2_collapse.md`, with
  `exploratory/e23_c04_collapse.py` and `e22`; control 2022 (same rules). Run once when the fetch ends.
- C-04 amendment 01 (before the run): the sealed rule kept only BUs with hash status "Totalizado" and would have
  dropped 16,522 boxes still "Recebido" at crawl time; they are now included and labelled
  (`commitments/c_test_04_amendment_01.md`). 517,287 listed sections = 499,176 boxes + 18,039 aggregated sections
  without files of their own + 72 not installed or without a log.

## 2026-10-28: author's decision, exploratory search on both halves
- The author: the aim now is to find every possible anomaly first and run focused checks on what is found
  afterwards. The half-C reserve ends here; from now on both halves are searched freely, at maximum sensitivity,
  with round 1 and 2022 shown as context only, never as filters. Sealed tests already run keep their results.
- E24 (`exploratory/e24_sweep.py`): per-box features of every log, both rounds, ranked by how many features are
  beyond the national round-1 0.1% tail.
- E24 first ranking discarded: round 1 is no yardstick for timing (several offices per voter in round 1, so every
  round-2 box looks fast). E24b (`exploratory/e24b_rank_r2.py`): robust z within the UF over round-2 boxes, rates
  per vote; paired with round 1 only for manual share and turnout. 498,902 boxes ranked (>= 30 votes);
  n features at z >= 4: 0: 439,205; 1: 55,500; 2: 4,024; 3: 167; 4: 6.
- Leads from E24b, for the BU check:
  - turnout: round-2 log votes / round-1 bweb attendance >= 1.2 in 132 boxes (Brazil, >= 30 votes) vs 44 in 2022
    (bweb vs bweb); >= 1.3: 23 vs 10; >= 1.5: 4 vs 5. Composition (aggregation, transit voters) to be checked
    with the round-2 BU aptos. Two top turnout cases (ES 56251/34/388, AM 2550/62/633) are partial round-1 logs
    (bweb attendance 218 and 315), not jumps.
  - round-2 log votes above round-1 aptos: 6 boxes (ES 56251/54/609, SP 70718/272/518, BA 33634/75/800,
    AL 27855/1/533, AL 27855/2/443, SP 71072/259/737); 2022 bweb had 0 with attendance above aptos. Pending the
    round-2 BU aptos (aptos changed between rounds in 49,464 sections in 2022).
  - manual enabling: 10 boxes went from < 50% manual in round 1 to >= 80% in round 2, 12 the other way
    (symmetric, consistent with reader failures; still listed).

## 2026-10-28: C-04 run once (amendment 01), and the BU check of the E24b leads
- C-04: 499,176 of 499,176 round-2 BUs fetched and parsed (482,654 Totalizado, 16,522 Recebido), 0 missing.
  Sum of the BUs: 22 59,825,504; 13 64,255,526; 48.2149% for 22 (official 48.2148%, rounding).
  2026 vs 2022 (tested 499,174 / 472,016): R0 (round 1 >= 10, round 2 = 0) 1 vs 0 (Fisher p 0.51);
  R1 (collapse, Bonferroni) 7 vs 24 (p 1.0); R1s 7 vs 32; R2 (>= 70% to a 20-point fall) 1 vs 2.
  Decision: **no signature found so far** for the reported pattern. The 2026 cases are listed in
  `reports/h8r2/c_test_04/flagged_2026.csv`; the only zero is AM 2615/5/176 (16 of 329 in round 1, 0 of 333);
  the only R2 case is AM 2097/18/37 (79.2% to 45.8%). AC 1139/7/67 is flagged in 2022 and in 2026.
- Votes above aptos (6 boxes): the round-2 BU aptos is higher than round 1 in all 6 (e.g. AL 27855/1/533: 459 to
  505); no BU anywhere has more votes than its aptos. Explained.
- BU total vs round-2 log votes: 1,435 boxes differ, BU always higher; all have one urn id in the log and a
  first vote late in the day (median about 11:00), consistent with a box replaced during the day (the published
  log covers the replacement only). Listed for H7r2.
- Turnout jumps with the BU (round-2 BU total / round-1 bweb attendance >= 1.2, >= 30 votes, Brazil): 133
  sections, composition unchanged in 132. Of the 110 found in 2022, none had a jump then (median ratio 1.00).
  Concentrated in MS indigenous-area municipalities (Amambai 16, Caarapo 9, Dourados 7, Paranhos 5; MS 48 in
  all), then Salvador 7, Rio 6. Extra votes went mostly to 13 (22 got 18.6% of the extra; 25% outside sections
  with 13 >= 90%). 5,803 extra voters, of whom about 994 extra manual enablings: about 83% of the extra came in
  by biometrics. Falls (<= 0.8): 672 in 2026 vs 533 in 2022. Kept as an open lead: `sweep/turnout_jumps_bu.csv`.
- Author's question, 2026-10-28: "in Santa Catarina Lula grew 25%". From the round-2 BUs and the round-1 bweb:
  13 in SC 1,127,168 to 1,418,314 (+25.8%), 22 3,000,020 to 3,220,071 (+7.3%); nationally +19.3% and +6.6%. The
  growth is real and follows the round-1 vote of the other candidates: SC had 373,893 such votes (14, 70, 55),
  blank and null fell by about 23,000, attendance rose 2.5%; 13 took 57% of the combined gain (SP 68%, RS 64%).
  Across SC's 295 municipalities, 13's gain = 0.75 x the round-1 vote of the others (R2 0.977); the largest
  residual is about 3,700 votes in a municipality with a 29,500 gain. Across UFs, 13's growth correlates 0.70
  with the others' round-1 share. 13's round-2 share in SC is 30.6% (2022: 30.7%). No anomaly found.

## 2026-10-28: author's hypothesis on the 17:00-19:00 window; round-2 bweb released; frozen round-2 audit run
Author's question: could an insider with strong engineering support have altered many boxes between 17:00 and
19:00 BRT (the extension), while TSE registered almost no receptions, and erased the evidence? The author left
analyses pre-authorised while away. Checks run (all exploratory unless they are the frozen H1r2-H7r2):
- E25 (`exploratory/e25_bu_emission.py`): the emission timestamp inside each of the 499,176 round-2 bu.dat files
  against the log's close. No BU was emitted before its close; median 2.6 min after. 1,129 boxes more than 30 min
  after, 553 more than 60 min, 28 more than 120 min.
- Same measure from the bweb (DT_EMISSAO_BU - DT_ENCERRAMENTO, > 30 min): 2022 r1 117, 2022 r2 42, 2026 r1 39,
  **2026 r2 686**. The excess is real and specific to the 2026 run-off. (The bweb emission time is the BU report;
  bu.dat is written after the printed copies, so the file stamp is 0-2 min later in 98.6% of boxes.)
- E26 (`exploratory/e26_late_bu_causes.py`): full log between "closing confirmed" and the writing of bu.dat, for
  2,703 late boxes (> 10 min) and a random control of 2,802 (2-5 min). **Votes computed after closing: 0. Voters
  enabled after closing: 0. Urn id changing inside that segment: 0.** Named causes in the late group: power cycle
  160, printer out of paper 75 (17 with a power cycle), other printer events 71. Example RJ 58971/135/195: BU
  report at 17:03, printer out of paper, box switched off 19:25, on 20:09, copies printed, bu.dat 20:13. In most
  of the rest the box waited at the post-voting poll-worker registration prompt before the BU (E26b).
- Round-2 bweb released by TSE (stamp 261020260742, per-UF resources dated 26.10.2026; the watcher saw them on
  2026-10-28T08:07Z). 28 files verified against TSE's SHA-512 and logged in data/manifest.jsonl; 499,205
  sections. `config/sources.json` gained the round-2 source (data, not a frozen file).
- Frozen audit H1r2-H5r2 (`exploratory/e27_round2_audit.py`, `reports/round2_2026/`), parameters from the frozen
  `config/round2_forensics.json`:
  - H1r2: 25 bins, 0 rejections at Bonferroni (0.0004), 0 at nominal 0.01; min p 0.015 (20:40 bin).
  - H3r2: one nationwide reception gap, 17:08 to 19:03 BRT (115 min), i.e. the extension. Reported as a process
    fact; the bins 17:10-18:50 are empty.
  - H4r2: I1-I5 and I7 0 violations; I6 8 (all in PA/PR, TSE reception 9-49 s before the box's emission time:
    box clock offset, as in round 1). Sum of the BUs equals TSE's final national file exactly: 22 59,826,041;
    13 64,256,232 (archive file generated 25/10/2026 23:27:02).
  - H5r2: of the 5,757 municipal files in the archive, 4,125 were at 100% when the collector stopped; in all
    4,125 the live result equals the sum of the BUs (the 41 abroad cities with 0 votes have no bweb row). 1,632
    files were not final in the archive and cannot be compared (BU >= live in all).
  - H2r2: no period qualifies as a publication freeze under the frozen definition (the 17:07-19:01 stillness had
    0.02% of sections received).
- H7r2 (`exploratory/e28_h7r2.py`, `reports/h7r2/`), logs vs bweb, local time:
  - H7a: every bweb section has a log entry; 43 log entries have no bweb row.
  - H7b: 1,464 vote mismatches; 1,422 explained (box replaced). Of the 42 others: 27 abroad sections where TSE
    lists no log; 3 boxes where the log has one "Voto confirmado" more than "voto computado" (bweb equals the
    confirmed count; one of them had a suspension and power cycle); 12 Brazilian boxes whose published log has
    no voting events: 5 are a **contingency box running the data recovery application (RED: "Recuperando urna
    de votacao com resultado nao gerado")**, 5 a contingency box loaded after 17:00 with no votes, 2 have no raw
    log kept (RJ 58653/144/7, SP 64777/395/298). The result of the original box was recovered from its media
    after closing: a documented procedure, and the closest real case to the author's scenario. Listed for the
    printed-BU check (`reports/h7r2/h7_discrepancies.csv`).
  - H7c: 0 close mismatches over 60 s. H7d: 32 (27 abroad without a log, 5 of the 12 boxes above).
    H7e: 11. 6 abroad (the local clock is not BRT); 5 Brazilian boxes with no "closing confirmed" in the log:
    ES 57932/9/112 and RJ 58653/144/7 (above), and MG 46256/131/46, RS 89630/72/54, SC 83593/8/143, which have
    full voting logs (votes equal bweb) but no closing event, with a suspension or power-off and the recovery
    media (RED) loaded afterwards: closing completed by recovery. bweb closes 18:31-18:52 local.
  - Extended sections (close >= 17:30 BRT): 7,612 by bweb, 7,613 by log.
- Exploratory cross-checks of the two TSE files: votes for 22 and 13 in the bweb equal the bu.dat in all 499,174
  joined sections (0 differences).
- What this does and does not show: no BU was produced or changed with votes after closing, and the BU files,
  the bweb, the logs and the published totals agree. A change made inside the box software before the BU is
  signed would not show in any of these (METHODOLOGY §6); the independent check for that is the comparison of the
  printed BUs (photographed at the sections from 17:00) with TSE's files, and the integrity-test reports.
- E26b (`exploratory/e26b_close_stages.py`, `sweep/close_stages.csv`): stage times in the same boxes, both rounds.
  Late group, round 2: median closing-confirmed to bu.dat 21.8 min (round 1, same boxes: 3.8; control: 2.7 and
  3.4). The delay sits in the **post-voting poll-worker registration step** (after closing is confirmed, before
  the BU report): over 30 min in 626 boxes in round 2 vs 1 in round 1; it ended at 17h (223), 18h (302), 19h
  (100) box clock. Then print end to bu.dat over 30 min in 290 (printer or prompt waits).
  - 77% of those 626 boxes are in a polling location where another section was extended (close >= 17:30 BRT),
    against 3.3% of all boxes; none was itself extended. Concentrated in Sao Paulo city (215), Rio (143),
    BA 38490 (88), PE 25313 (54). Reading: in locations under the extension, sections that had already closed
    waited before issuing their BU until the location finished. They could not take votes (E26: 0 votes, 0
    enablings after closing). The cause of the wait (instructions to poll workers) is not in the data.
- H6r2 (`exploratory/e29_h6r2.py`, `reports/h6r2/`), frozen `tally/extension.py`, 10,000 permutations, seed
  20261025, Bonferroni 0.01/7 = 0.00143. ZZ excluded, sections with >= 30 two-candidate votes in both rounds.
  - Calibration §4.1 (2022 run-off real late closers, 333 sections): H6a share/turnout/blank-null p 0.34 / 0.026 /
    0.21; H6b not computable (no 2022 municipality with >= 50% late); **H6c false alarm** (6 of 333 flagged,
    p 6.6e-5). By the fixed rule, H6c in 2026 is reported as descriptive only. §4.2 (200 placebo label draws)
    not run yet: about 2,800 permutation tests at this code's speed; pending, the author decides.
  - 2026 primary (17:30 BRT, 7,612 extended of 497,708): **H6a d_share +0.049 pp, p 0.029: not rejected**
    (the headline). H6a d_turnout +0.185 pp and d_blank_null +0.083 pp: p 0.0001, rejected; extended sections
    gained slightly more turnout and blank/null than on-time sections of the same municipality, both well under
    half a point (more turnout is what an extension is for). H6b: share -0.18 pp p 0.40, turnout -1.4 pp p 0.066,
    blank/null -0.49 pp p 0.044, none rejected. H6c (descriptive only): 22 of 7,612 flagged (expected 15),
    p 0.060; list in `h6c_flagged_2026_primary.csv` for the printed-BU check.
  - Sensitivity 18:00 BRT and local clock: same decisions (H6a share p 0.22 and 0.035).
  - Not yet run: H6r2 by the log method (H7r2 §3; the log and bweb extended sets differ by 1 section).
