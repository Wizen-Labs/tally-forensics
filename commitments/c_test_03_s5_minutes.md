# Sealed test C-03: S5 lead, section minutes of flagged vs control sections (H8r2 §0)

Fixed on 2026-10-27, before any minute was requested or received. Lead and context: `reports/h8r2/hunt_log.md`
(entries "sealed test C-02" and "S5 lead (C-02): minutes to request"). Sample:
`reports/h8r2/s5_minutes_request.csv` (30 pairs, half C: one S5-flagged section and one unflagged control of the
same zone). Analysis: `exploratory/e21_c03_minutes.py`, input template `data/minutes/s5_minutes_answers_template.csv`;
their SHA-256 is sealed with this file. Run once, when the answers are in; every result is reported.

## Explanation under test
The S5 flags mark sections where who authorises manual enablings changed between rounds (a different poll worker,
or the reader or poll-worker biometrics behaving differently). The minutes record who served and the occurrences.

## Data (from the TRE answers, no personal data)
Per section: for each role (president, 1st mesário, 2nd mesário, 1st secretary, 2nd secretary), whether the same
person served in both rounds (yes / no / not applicable); substitutions during the day in each round (yes / no);
an occurrence about poll-worker biometrics, manual enabling or the fingerprint reader in each round (yes / no).
Answers are typed into a copy of the template exactly as received; a missing answer is left empty.

## Outcomes per section
- **O1 (turnover):** at least one role answered "no" (a different person in round 2).
- **O2 (biometric occurrence):** an occurrence about poll-worker biometrics, manual enabling or the reader in
  either round.
A section counts for an outcome only if every field that outcome uses is answered ("not applicable" counts as
answered and is not a change).

## Test
- Paired: for each outcome, the pairs where both sections are answered. One-sided exact McNemar (binomial on the
  discordant pairs, flagged = 1 / control = 0 against flagged = 0 / control = 1, p0 = 0.5). Holm over O1 and O2.
- alpha 0.05 (small sample, stated in advance).

## Decision
- Fewer than 15 complete pairs for both outcomes: **inconclusive**; reported as such, with what arrived.
- O1 or O2 with Holm p < 0.05: **explanation supported**; the S5 lead is closed as poll-worker turnover or reader
  and biometric occurrences.
- Otherwise, if the share with O1 or O2 among flagged sections is not above that among controls: **explanation
  not supported**; the 30 flagged sections become an unexplained pattern for physical check (poll-worker
  registration records, the reader logs, the boxes).
- Otherwise (higher in flagged, not significant): **inconclusive**; reported with the effect and the counts.
- A per-role table and the counts of every field are reported in all cases.
