# Protocol addendum H8r2: signature search in box logs and section transfers (26 October 2026)

**Project** · tally-forensics · round-2 audit, addendum
**Status** · Fixed on 2026-10-26, before any per-section round-2 figure was analysed and before TSE published the
round-2 bweb files. The SHA-256 of this file, `tally/signatures.py` and `tally/full_logs.py` is timestamped with
OpenTimestamps (`commitments/round2_signatures.sha256`).
**Rule** · Any later change is a logged deviation. Every result is reported, including those that look bad.

## 0. Objective and stance
- **The box is a black box.** Its BU, digital vote record (RDV) and log are all produced by the same software.
  Consistency checks (H1r2–H7r2) can show that the published files agree with each other. They cannot show that the
  software counted correctly. **This project therefore never states that the result is correct.** At most it states
  that no signature was found with the data and methods used.
- **The objective of H8r2 is to hunt for anomalies** and follow each one until it either has an ordinary explanation
  or becomes a **signature**. A signature is a pattern that a process driven by many independent human actions
  would not produce, shown on data that were not used to find it.
- **The hunt is free; the proof is sealed.** The 27 UFs are split at random into two halves (§2):
  - **Discovery (D):** any number of looks, any method. Every look is written to a hunting log
    (`reports/h8r2/hunt_log.md`), including the ones that find nothing.
  - **Confirmation (C):** not analysed until a candidate signature from D is written down as a test, with its rule,
    and timestamped. The test is then run once on C.
- **The fixed detectors (§3, §4)** run on both halves from the start. They are the first look, not the last.
- **Wording:** a signature is reported as an **"unexplained pattern"**, listing the sections. It is a reason for a
  physical check of those sections (paper BUs, the boxes themselves). The word fraud is not used.
- **What can and cannot be searched:**
  - The log never records the choice, and the RDV is shuffled by design. The sequence of choices therefore cannot be
    searched by anyone.
  - The log does record, for every voter, the full trail with times:
    - the identifier typed by the poll worker (voter card or CPF; type only);
    - the photo shown;
    - fingerprint requests, attempts and match scores;
    - the enabling type, biometric or manual;
    - the offices confirmed;
    - "O voto do eleitor foi computado".

    A vote that did not come from a person needs a fabricated human trail. Fabricated trails tend to be too fast,
    too regular, periodic, repeated or synchronised across boxes. The section-level transfer between rounds can be
    too uniform.
- **Seen before this file was fixed:**
  - the national totals of both rounds;
  - the event vocabulary of one round-2 log from RJ (counts of event types only);
  - the round-1 lines of that log.

  No per-section round-2 figure has been analysed.

## 1. Data
- **Logs:**
  - the full raw log of every section;
  - after the H7r2 crawl, a second pass (`tally/full_logs.py`) fetches every log that H7r2 summarised but did not
    keep, at most 30 requests/s. The H7r2 code is not changed. Each file must match the SHA-256 that H7r2 recorded,
    or it is not stored.
- **Per-voter trail** (`signatures.trails`): the events from "Aguardando digitação do identificador do eleitor" to
  "O voto do eleitor foi computado", for 25/10/2026 (round 2) and 04/10/2026 (round 1).
  - Kept: the times (in seconds), the identifier type, photo, fingerprint attempts, number of scores and last score,
    the enabling type, the offices confirmed, invalid key presses.
  - **No personal data is stored.** The poll workers' voter numbers are replaced while reading by a per-box index
    (1, 2, …).
- **Software load** (`signatures.software`), from the lines dated 05/10 to 25/10/2026:
  - the application version;
  - the box model;
  - the set of signature-checked files;
  - the result of each check.
- **Bulletins:** bweb round 1 and round 2 of 2026 and of 2022, verified by SHA-512 and read with the frozen parser.
- **Sections are matched** across rounds by (UF, municipality, zone, section). Aggregated sections are excluded. For
  the paired log detectors (S2, S5), so are sections that changed box between rounds or whose box was replaced
  (H7r2 rule). All exclusions are listed.

## 2. Controls and halves
- **Round-1 control (log detectors).** Each detector is computed for round 1 of the same boxes in the same way,
  with round 1's own reference distribution. The round-1 flagged count is the control. Timing is never compared
  directly across rounds, because round 1 had six offices on the ballot and round 2 one or two.
- **2022 control (transfer tests):** the same sections, round 1 to round 2 of 2022. That year about 9.9 million
  votes went to other candidates, against 9.3 million in 2026.
- **Halves** (`signatures.split_ufs`, seed 20261026): 13 UFs in D, the other 14 plus abroad (ZZ) in C.

## 3. Fixed detectors on the box logs (S1–S7)
- **Common rule:** each section gets a p-value. A section is **flagged** below 0.01 / (number of sections), which is
  Bonferroni over sections.
- **Reference group** (S1): the UF and the box's modal number of offices per voter.

| ID | Signature | Statistic (code) | Control |
|---|---|---|---|
| **S1** | Turbo | Votes whose "Eleitor foi habilitado → O voto do eleitor foi computado" time is at or below the group's 0.1% quantile, more concentrated in one box than binomial(n, p0) allows. p0 is the group's share at or below the quantile (`s1_turbo`) | round 1 |
| **S2** | Zombie | (a) manual enablings, round 2 vs round 1 of the same box, one-sided Fisher exact; the reverse direction is the control. (b) The longest run of consecutive manual enablings, exact probability under random order (`p_longest_run`). (c) The most voters enabled by one poll worker, descriptive (`s2_zombie`) | (a) reverse; (b) round 1 |
| **S3** | Periodicity (the classical form of Shor's period finding) | Fisher's g with its exact p-value on three series per box with at least 64 votes: log inter-vote interval (minus a 15-vote moving mean), enabling type and fingerprint attempts. Bonferroni over boxes × series (`s3_periodicity`) | round 1 |
| **S4** | Repetition | Blocks of 10 consecutive voter trails identical in all codes and in the three intervals (identifier, enabling, vote), found in two or more boxes. 64-bit rolling hash (`s4_repetition`) | round 1 |
| **S5** | Fingerprint scores | Chi-square of each box's round-2 scores against its round-1 scores, on the deciles of the national round-1 scores (at least 20 in each round). The control is the same test between round-1 even- and odd-numbered voters (`s5_scores`) | split round 1 |
| **S6** | Synchrony (one trigger) | Minutes (BRT, using the frozen UF/municipal offset) in which a box's vote count has Poisson p < 1e-6 against its own rate. The statistic is the most boxes spiking in one clock minute; 200 random circular shifts of each box's spikes give the p-value (`s6_synchrony`) | round 1 |
| **S7** | Software | Within each box model: boxes whose version or file set differs from the mode, any check that did not report SUCESSO, or no check at all (`s7_software`) | deterministic |

- **Decision rule for S1–S6** (`decide`, per half), all of the following:
  1. the flagged count is at least 2× the null expectation (0.01) and at least 2× the control;
  2. the excess over the control has one-sided binomial p < 0.01, Holm-adjusted across S1–S6;
  3. the excess is present in both D and C.
- **S7:** every box listed is reported.
- **Flagged sections are leads even when the rule is not met.** They are followed in D under §0, and any resulting
  candidate signature goes to C as a new sealed test.

## 4. Fixed section-transfer tests (T1–T4): too homogeneous, too uniform
- **Notation.** For each section (`transfer_frame`):
  - E is the electorate (at least 50);
  - A1 and A2 are Lula's votes in rounds 1 and 2;
  - B1 and B2 are Flávio Bolsonaro's;
  - the other candidates of round 1 are taken separately for the four largest and pooled for the rest;
  - BN is blank plus null; T is turnout;
  - d = (A2 − A1) / E.
- 2022 is built the same way (Lula, Bolsonaro).

| ID | Question | Rule |
|---|---|---|
| **T1** | Is the transfer more homogeneous than chance allows? | Per municipality with at least 10 sections: R = var(d) / mean binomial variance of d (`t1_dispersion`). **Signature:** the share of municipalities with R ≤ 1 in 2026 is at least 2× that of 2022, with one-sided two-proportion p < 0.01 (`t1_compare`) |
| **T2** | Do many sections repeat almost the same change? | The share of sections inside the densest 0.5-pp window of the T4 residuals (in pp of E). **Signature:** 2026 ≥ 1.5× 2022, with p < 0.01 from 500 bootstrap draws over municipalities (`t2_spike`) |
| **T3** | Do many sections show the same absolute increment? | Count the sections whose A2 − A1 equals their municipality's modal increment. Null: 1,000 permutations of the relative change (A2 − A1)/A1 among sections of the same municipality and similar size (E in one 5% log-bin), applied to each section's own A1 (`t3_same_increment`). **Signature:** p < 0.01 in 2026 and an excess ratio larger than 2022's |
| **T4** | Is there an increase that the sources do not explain? | OLS of A2 − A1 on E, each other candidate's round-1 votes, the fall in blank+null and the change in turnout, with errors clustered by municipality (`t4_regression`). The intercept **a** is a uniform additive increase per box. **Signature:** a_2026 > 0 and the 99% interval of a_2026 − a_2022 excludes 0 (`t4_compare`) |

- **Also reported, without a decision rule:**
  - the turnout × Lula-share fingerprint (Klimek et al. 2012), for 2026 round 2, 2026 round 1 and 2022 round 2
    (`fingerprint`);
  - the transfer rate from each other candidate (T4);
  - the sections with turnout at or above 95%.
- **The competing explanation is checked in every test:** T1–T4 are rerun without the sections extended to 19:00
  (H6r2 set). The share of the national turnout rise that falls in extended sections is reported.

## 5. Synthetic checks (`tests/test_signatures.py`, part of the frozen code)
- **No false alarms on clean data:** on simulated independent human trails and heterogeneous transfers, each
  detector flags at most one box, or has p > 0.01.
- **Power:** each detector finds its injected pattern:
  - 40 votes in zero seconds (S1);
  - 40 manual enablings in a row (S2);
  - every 5th voter enabled manually (S3);
  - a copied 10-voter block (S4);
  - one repeated score (S5);
  - 50 boxes spiking in the same minute (S6);
  - identical transfers (T1);
  - +15 votes per section (T4);
  - +12 votes exactly in half the sections (T3).
- **One defect was found and fixed before the freeze.** A first T3 permuted the round-2 counts directly, which broke
  the link between a section's two rounds and gave false alarms on clean data (p = 0.005).

## 6. External evidence (listed, not tested here)
- TSE's integrity test (parallel voting on sampled boxes on election day): the published results for 2026 round 2.
- The paper BUs printed at the sections: if an independent set of photos becomes available, compare a sample,
  starting with the flagged sections.
- The public software inspection and the hash of the signed software (S7 compares the boxes with each other only).

## 7. Order of work
1. Fix this file and the code: hash and OpenTimestamps.
2. Run the H7r2 crawl, then the full-log second pass.
3. Run S7 and S1–S6 on both halves. Open the hunt on D.
4. When the round-2 bweb is out: run H1r2–H7r2, then T1–T4 with the 2022 control, on the whole country.
5. Seal each candidate signature from D as a test, timestamp it, and run it on C.
6. All results go to FINDINGS.md (entry H8r2), signature or not, with the same prominence.
