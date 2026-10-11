# Methodology and pre-registration

**Project** · tally-forensics · statistical audit of the Brazilian presidential tally from public TSE ballot-box reports
**Status** · DRAFT, protocol **not frozen** · v0.2 · 2026-10-11
**Rule** · This document is written before the 2026 data are analysed. Once the owner sets `"protocol_frozen": true`
in `config/analysis.json`, any change is a protocol deviation and is logged in `FINDINGS.md` with its reason.

---

## 1. Question

On 2026-10-04, the national presidential tally on TSE's results site stopped updating at about 64% of sections from
roughly 19:00 BRT and resumed at 20:08 BRT at 84.96%. TSE attributed it to data congestion and said only the
*publication* of the national presidential result paused; reception and counting continued.

We ask two things, using only public, hash-verified TSE data:

1. **Temporal:** do the sections that reached TSE during that window, or at any other time, behave differently from
   comparable sections that reached TSE at other times?
2. **Geographic:** are there states or municipalities whose sections disagree with their own neighbours more than
   chance allows?

The aim is a falsifiable test. A clean result is reported with the same prominence as an anomaly.

## 2. Data

### 2.1 Source
- TSE open data, *Boletim de Urna* (`bweb_1t_<UF>_<stamp>.zip`), one file per UF plus `ZZ` (abroad).
  2026 stamp `051020261403`, 2022 stamp `051020221321` (`config/sources.json`).
- Every file is checked against the `.sha512` TSE publishes next to it, and logged in `data/manifest.jsonl`.

### 2.2 Unit
One row per section (`SG_UF, CD_MUNICIPIO, NR_ZONA, NR_SECAO`) for office code 1 (President), with all candidate
votes, blank, null, eligible voters, turnout, the box serial number and four timestamps.

### 2.3 Clocks (verified on RR 2026 and RR/AC 2022)
- `DT_ABERTURA`, `DT_ENCERRAMENTO`, `DT_EMISSAO_BU` are the **ballot box's local clock**: in RR (UTC-4) boxes open at
  07:00 and close at 16:00, i.e. 08:00/17:00 BRT.
- `DT_BU_RECEBIDO` is **TSE reception in BRT**: in RR 2026 the earliest reception is 17:08, eight minutes after the
  national close, which only fits a BRT clock.
- Polls open at 08:00 BRT nationwide, so each municipality's offset is the modal opening hour subtracted from 8
  (checked: AC +2 h, RR +1 h). Abroad (`ZZ`) the offset cannot be inferred and `ZZ` is excluded from temporal tests.
- `DT_BU_RECEBIDO` is not documented in TSE's *leiame*. The BRT reading is an inference; check I7 (no reception before
  17:00 BRT) tests it on every run.

## 3. Baseline: within-location residual (R1)

Sections in the same polling location (same building, `NR_LOCAL_VOTACAO` within zone) serve near-identical
neighbourhoods. For section *i*, with *a* votes for candidate A among *v* valid votes:

```
resid_i = a_i / v_i  -  (sum of a over sibling sections) / (sum of v over sibling sections)
z_i     = resid_i / sqrt( p_sib (1 - p_sib) (1/v_i + 1/v_sib) )
margin_resid_i = resid_A,i - resid_B,i
```

Sections with fewer than 30 valid votes, or with no sibling, get no residual.

**Why this baseline:** it needs no model, no other election and no polls, so there is nothing to tune. Geography,
local politics and turnout culture are shared by siblings and cancel out.

**What it cannot see:** a shift applied uniformly to every section of a location, a municipality or the whole
country. No section-level statistic can detect that; see §6.

## 4. Hypotheses (pre-registered)

| ID | Null hypothesis | Test | Role |
|---|---|---|---|
| **H1** | After adjustment for pre-transmission covariates (§4.2), sections received 19:00 to 20:08 BRT have the same mean `margin_resid` as their own location siblings received outside the window | Within-location permutation (2,000 permutations, seed 20261004), two-sided | **Primary**, alpha = 0.01 |
| H2 | Same, for adjusted `a_resid` and the adjusted turnout residual | Same test | Secondary, Holm-adjusted |
| H2u | H1 without adjustment | Same test | Reported for transparency; known to be confounded (§4.2) |
| H3 | Reception did not stop during the publication freeze (TSE's claim) | Sections received per 10-min bin inside the window vs. adjacent bins | Descriptive |
| H4 | Integrity checks I1 to I7 have zero violations; the sum of BUs equals TSE's official totals exactly | Deterministic | Factual |
| H5 | No UF or municipality has an extreme mean residual | Geographic summaries and UF x time heatmap | **Exploratory only** in v0.1 |

Integrity checks:
- **I1:** presidential votes = turnout.
- **I2:** eligible voters = turnout + abstentions.
- **I3:** turnout ≤ eligible voters.
- **I4:** section keys are unique.
- **I5:** each box serial number is used by only one section.
- **I6:** the clocks run in order: opening < closing ≤ BU emission ≤ reception.
- **I7:** no BU is received before 17:00 BRT.
- **R-nn:** the sum of the BUs for each candidate equals the official total.

### 4.1 Decision rule for "anomaly"
H1 counts as an anomaly signal only if **all** of these hold:
1. p < 0.01 in the primary window;
2. the same sign in the three sensitivity windows (start ±15 min, end +15 min);
3. no rejection in the two placebo windows (17:52 to 19:00 and 20:08 to 21:16);
4. no rejection when the identical clock window is tested on the **2022** first round, where no freeze happened.

Even then the conclusion is "a pattern that needs an explanation". It is not "fraud". Known innocent explanations
must be checked first (§5).

### 4.2 Covariate adjustment (added after the 2022 calibration, before any 2026 analysis)
In the full 2022 calibration the unadjusted test rejected in the 20:08 to 21:16 placebo window (p = 0.001), in an
election with no freeze. Exploration found two innocent, pre-transmission causes:
- **Queues.** Sections that close late lean differently from their own siblings: −0.68 pp margin residual when
  closing more than 2 h late. Their BUs arrive late (median close delay 20 min in that window, against 4 min
  elsewhere).
- **Section rank.** The newest sections in a location (top quintile of section number) differ by −0.72 pp.

The primary test therefore first removes, within location, the part of the residual explained by:
- the close-delay bucket (≤5, 5–15, 15–30, 30–60, 60–120, >120 min after 17:00 BRT);
- the section-rank quintile within the location;
- the log of eligible voters;
- the aggregated-section flag.

The coefficients are fitted on **out-of-window sections only**, so the adjustment never sees the window it tests.
All of these covariates are fixed at the polling station **before** the BU leaves the box, so they cannot absorb a
manipulation that happens in transmission or totalisation. They could absorb a manipulation targeted at
late-closing sections, which is a stated limitation. The synthetic tests show the adjusted test ignores a pure
queue effect and still detects a 5% shift injected into the window.

### 4.3 Exploratory findings
Anything from H5, from the fingerprint plot, or from the last-digit test is exploratory. It may motivate a new
pre-registered test on the second round (2026-10-25). It is never reported as a finding on its own.

## 5. Known confounders and how they are handled

| Confounder | Why it matters | Handling |
|---|---|---|
| Arrival order is not random | Remote, rural and Northern sections arrive later and vote differently | The within-location design compares a section only with its own building |
| Section number and voter cohort | Newer sections often hold newly registered (younger) voters; if they also close later because of queues, they arrive later | Section-rank quintile is a covariate in the primary test (§4.2) |
| Aggregated sections (`DS_SECOES_AGREGADAS`) | More voters, longer queues, later close | Aggregated flag is a covariate in the primary test (§4.2) |
| Contingency boxes and boxes not counted (`CD_TIPO_URNA` ≠ 1) | Different handling path | Excluded from tests, counted in the summary |
| Over-dispersion | Real sections vary more than binomial noise | Permutation tests are immune; the scale is reported, never tuned |
| Multiple comparisons | Many windows x metrics x areas | One primary test; Holm on the secondaries; everything else exploratory |

## 6. What this analysis cannot establish
- **Inside the ballot box.** The BU is produced by the box itself. If the box software altered votes uniformly, the BU,
  the transmission and the totalisation would all agree, and nothing here would notice. Software inspections, public
  security tests, the integrity test with parallel voting, and hash and signature checks address that layer; this
  project does not.
- **Independence of the reconciliation.** R-nn compares TSE's per-section files with TSE's published totals. It tests
  the transmission and totalisation layer for internal consistency. Independent ground truth would be BU printouts or
  QR codes collected by observers at the sections (a v0.3 idea).
- **Intent.** A statistical deviation never identifies who or why.

## 7. Calibration before confirmation
1. Run the whole pipeline on **2022, round 1, all UFs**. It is calibration data, and parameters may still change here.
2. Record the calibration results in `FINDINGS.md`.
3. The owner reviews them and sets `protocol_frozen: true`.
4. Run 2026, round 1, all UFs, once. Report everything.
5. Pre-register the 2026 second round (2026-10-25) before that election happens.

## 8. Reproducibility
- Python 3.11. Dependencies are in `requirements.txt`. Fixed seed.
- The raw zips are verified by SHA-512 and never overwritten.
- `python -m pytest` includes **power and false-alarm tests**: a synthetic election with a 5% shift injected into the
  window must be detected, and three clean synthetic elections must not be flagged.
