# Commitments: phase B, the live run-off projection

Besides the forensic audit in this repository (phase A), the project has a **second, separate pre-registration:
phase B**. It is a live statistical projection of the 2026 presidential run-off (25 October 2026), made from the first
sections counted, using only TSE's public live results.
- It runs on two independent systems: a main one and a backup.
- It publishes nothing before 2% of sections are counted and 24 of the 27 states have data.
- It calls a winner only when the whole pre-registered interval lies on one side of 50%.

Its documents and code stay private until after the election, so that the method cannot be changed after the
results are seen. They were frozen on 2026-10-20 at 13:57 (UTC+1), before the election. This folder commits to their
exact content:

- `round2_projection.sha256` lists the SHA-256 of every frozen phase-B file, in `sha256sum` format.
- `round2_projection.sha256.ots` is an [OpenTimestamps](https://opentimestamps.org) proof that the list existed on
  2026-10-20. It was submitted at 14:27 (UTC+1) to four public calendars, which anchor it in the Bitcoin blockchain.

**Verify the timestamp** with the standard client:
```bash
pip install opentimestamps-client
ots verify commitments/round2_projection.sha256.ots
```
`tools/ots_stamp.py` stamps and upgrades proofs without the `ots` command, because that command does not run on
Windows.

**Verify the content after the reveal:** after the election the phase-B files will be published in this repository,
unchanged. Then, from the repository root:
```bash
sha256sum -c commitments/round2_projection.sha256
```
Every line must print `OK`. Projection results are reported in full, including errors outside the interval.

**Note on `PREREGISTRATION_ROUND2.md`:** the hash in the list is that of the lab version, which has one extra
section, §5, announcing phase B. That section is not in the published file, so this one line will only match after
the reveal. The published file's own hash is in `FINDINGS.md`.
