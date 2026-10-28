# Sealed test C-04: sections where candidate A collapsed or fell to zero in round 2 (H8r2 §0)

Fixed on 2026-10-28, before any round-2 vote count was read (one Acre section, half D, was parsed to check the file
format). Question from the author: reports that, in some sections, Flavio Bolsonaro (22) had very large round-1 votes
and collapsed or got zero in round 2. Round-2 votes per section come from each section's `bu.dat` on TSE's results
site, fetched by `exploratory/e22_fetch_bu_r2.py` (manifest with SHA-256 per file); round 1 from the bweb
(`sections_2026_t1.parquet`). Control: the same rules on 2022 (Jair Bolsonaro, 22), bweb rounds 1 and 2. Analysis:
`exploratory/e23_c04_collapse.py`, sealed with this file. Run once, on both halves; every result is reported.

## Data per section
- Round 1: F1 = votes for 22, V1 = votes for all presidential candidates (blank and null excluded), aptos.
- Round 2 (2026, from the BU, election 6258): F2 = votes for 22, L2 = votes for 13, aptos. Only the BU of the hash
  whose status is "Totalizado"; a section without one is listed as missing.
- 2022 round 2 from the bweb (`sections_2022_t2.parquet`).
- Join on (UF, municipality, zone, section). Unmatched sections are counted and listed.
- `composition_changed`: aptos differ between the rounds by more than 5% (aggregation or transfers). Such sections
  are tested and labelled, never dropped.

## Quantities
s1 = F1 / V1; n2 = F2 + L2; s2 = F2 / n2. Tested: V1 >= 10 and n2 >= 10. m = median of (s2 - s1) over the tested
sections of the same municipality and year. Expected round-2 share p = clip(s1 + m, 0.005, 0.995).
z = (F2 - n2 p) / sqrt(n2 p (1 - p)); phi = (1.4826 MAD(z))^2 over the tested sections of the year (at least 1);
p_od = Phi(z / sqrt(phi)) (lower tail). Also the plain binomial lower tail P(X <= F2 | n2, p), reported.

## Detectors (both years, same code)
- **R0 (zero):** F1 >= 10 and F2 = 0. Every case is listed.
- **R1 (collapse):** p_od < 0.05 / N, N = tested sections of that year (Bonferroni).
- **R1s (sensitive list):** Benjamini-Hochberg q < 0.05 on p_od.
- **R2 (descriptive, as reported):** s1 >= 0.70, s2 <= s1 - 0.20, V1 >= 50.
Each flagged section is listed with F1, V1, F2, L2, both aptos, `composition_changed`, the half, and the round-2
log vote count (E12) for comparison with n2 plus blank and null.

## Integrity check (reported)
Sum of F2 and L2 over all fetched BUs against the official round-2 result (22: 48.2148% of the two-candidate vote).

## Decision
- 2026 R0 or R1 count above 2022 (one-sided Fisher exact on the tested denominators, p < 0.05, separately for R0
  and R1, Holm over the two): **unexplained pattern**; the excess sections go to physical check (BU paper copy,
  RDV, minutes).
- Otherwise: **no signature found so far** for the reported pattern; the 2026 R0, R1 and R2 cases are still listed
  with their labels, as sections that resemble the reports.
- If fewer than 95% of round-2 sections have a BU, the result is reported as partial, with the missing list.
