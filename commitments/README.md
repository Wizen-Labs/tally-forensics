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
  It is **anchored in Bitcoin block 972,335** (mined 2026-10-20 13:57:43 UTC), and again in block 972,338.

**Verify the timestamp** with the standard client:
```bash
pip install opentimestamps-client
ots verify commitments/round2_projection.sha256.ots
```
`tools/ots_stamp.py` stamps and upgrades proofs without the `ots` command, because that command does not run on
Windows.

**Revealed on 2026-10-28.** The phase-B files are now published in this repository. The frozen copies, taken from
git tag `round2-prereg`, are in [`reveal_round2_prereg/`](reveal_round2_prereg/). Verify them with:
```bash
cd commitments/reveal_round2_prereg
sha256sum -c ../round2_projection.sha256
```
Every line must print `OK`. The election-night evaluation (FINDINGS P12) reports the projection results in full.

**From the repository root,** 7 of the 8 lines print `OK`. `colab/tally_colab.py` fails there by design: three
lines of the media card's drawing code changed on 2026-10-24, after the freeze and before the election. The change
is presentation only and is disclosed in FINDINGS (Protocol deviations, 2026-10-24). The frozen version is the one
in the folder above.

**Note on `PREREGISTRATION_ROUND2.md`:** the hash in the list is that of the lab version, which has one extra
section, §5, announcing phase B. Until the reveal, the published file omitted that section and had its own hash
(in `FINDINGS.md`). Since the reveal, the published file is the lab version, and its line verifies.
