# Protocol addendum H7r2: ballot-box logs vs ballot-box reports (26 October 2026)

**Project** · tally-forensics · round-2 audit, addendum
**Status** · Fixed on 2026-10-26, **before TSE published the round-2 ballot-box (bweb) files**. The SHA-256 of this
file and of `tally/urna_logs.py` is timestamped with OpenTimestamps (`commitments/round2_logs.sha256`).
**Rule** · Any later change is a logged deviation. Every result is reported, including those that look bad.

## 0. Why
- On 25 October voting was extended to 19:00 BRT in some places by an official decision. The author asked for a
  stricter audit of that day, by two independent methods, cross-checked.
- TSE publishes the same day in two ways:
  1. the **bweb files**, one per UF, with a SHA-512 (the source of the frozen tests H1r2–H6r2);
  2. **per-section files** on `resultados.tse.jus.br` (`arquivo-urna/3221/...`), including each box's event log
     `logd.dat`. The log has a time for every vote, the opening and the close.
- If both come from the same boxes, they must agree. H7r2 checks that, section by section.
- These are **consistency checks between two TSE publications**, not statistical tests. A mismatch is reported as
  an "unexplained discrepancy" and listed in full; it is **never** described as fraud.

## 1. Data
- **Logs:** `tally/urna_logs.py` fetches, for every section in TSE's round-2 section list (`-cs.json`), the
  `-aux.json` and every `-log.jez` it lists, at most 30 requests/s.
  - Each log's SHA-256 is recorded.
  - The raw log is kept for sections with a round-2 close at or after 17:30 local time, for unusual logs, and for a
    1% sample by hash.
  - Only the lines dated 25/10/2026 are used for round 2 (and 04/10/2026 for the round-1 validation). Times are
    the box's local clock.
- **bweb:** the round-2 files, verified against TSE's SHA-512, with the frozen parser.
- The bweb times (`DT_ABERTURA`, `DT_ENCERRAMENTO`) are compared in **local time**, as written by TSE, so no time
  zone conversion enters H7r2.

## 2. Checks (round 2; all 28 UFs, abroad included)

| ID | Check | Pass rule |
|---|---|---|
| **H7a** | Coverage | Every bweb section has a log, and every section with a log is in bweb (TSE's aggregated sections have no folder and no bweb row) |
| **H7b** | Votes | Count of "O voto do eleitor foi computado" on 25/10, summed over the section's logs, equals `QT_COMPARECIMENTO` |
| **H7c** | Close | The last "Procedimento de encerramento confirmado" on 25/10 is within 60 s of `DT_ENCERRAMENTO` |
| **H7d** | Box | The log's box number equals `NR_URNA_EFETIVADA` |
| **H7e** | Extension | The extended set (close at or after 17:30 BRT, §2 of H6r2) is the same from the log and from bweb |

- **Explained category (fixed from the round-1 calibration in §4):** a box **replaced during voting** has a log that
  starts after the section opened and lacks the votes cast before the replacement.
  - The rule: the log's first "Urna pronta para receber votos" is more than 5 min after `DT_ABERTURA`, and the log
    has fewer votes than bweb. That case is classified "explained: box replaced".
  - It is still listed. Everything else that fails H7b–H7e is "unexplained" and is listed with both values.
- **Expected result:** zero unexplained discrepancies. Any count above zero is reported with the same prominence as
  a clean result.

## 3. H6r2 by the second method
- H6a–H6c are run a second time with the extended flag taken from the log's close (same 17:30 BRT cutoff, same
  code, same seed). The log time is converted to BRT with the UF's offset that the frozen pipeline uses for bweb.
- Both runs are reported side by side. If the two methods disagree on a test's decision, that is reported, and
  neither run is chosen over the other.
- **Exploratory (E8), not a test:** the timing of votes after 17:00 BRT in extended sections (how many people voted
  in the extension, by UF and hour).

## 4. Calibration already done (round 1, Roraima, before this file was fixed)
- 1,627 sections in TSE's list. 108 had no folder: these are exactly the aggregated sections, absent from bweb.
- 1,494 sections used the same box in both rounds, so their round-2 log also holds the round-1 events. Against the
  round-1 bweb:
  - the votes matched exactly in 1,492;
  - the close was 0–1 s apart in all 1,494;
  - the box number matched in all.
- The 2 vote mismatches are boxes replaced during voting: the log starts at 07:44 and at 08:29 local, against an
  opening at 07:00, and lacks 8 and 10 votes. This defined the explained category in §2.
- 25 sections changed box between rounds, so their log has no round-1 events.
- Before the round-2 bweb is analysed, the same round-1 validation runs on every UF and is reported (FINDINGS E8).

## 5. Order of work
1. Collect the logs, then run the round-1 validation for every UF (§4).
2. When TSE publishes the round-2 bweb, run the frozen H1r2–H5r2, then H6r2 (bweb).
3. Run H7a–H7e, then H6r2 by the log method (§3), then E8.
4. All results go to FINDINGS.md (entry H7r2), clean or not, with the same prominence.
