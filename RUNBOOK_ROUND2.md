# Runbook: election night, 25 October 2026 (lab only)

Both pre-registrations are frozen (tag `round2-prereg`, 2026-10-20). **Do not change any frozen file before or during
the night.** All times are BRT. UK time is BRT + 3 h on 25 October: the UK leaves summer time at 02:00 that day, and Brazil has no summer time.

## Roles

| System | Where | Model and interval | Publishes? |
|---|---|---|---|
| **Main** | desktop, `tally live --project` | mean of transfer + swing, ±0.7 pp | **yes**, the project's number |
| **Backup** | author's Colab, `colab/tally_live_independent.ipynb` | swing, ±0.8 pp | only if the main system fails |
| Helpers | son's and nephew's Colab (`HELPER_NAME` set) | as backup | **never** (watermark "BACKUP · NÃO PUBLICAR") |

**Gate (both systems):** at least 2% counted **and** 24 of the 27 UFs with 1% counted. It is expected at about 17:30.
**Call:** only outside 49.3–50.7% (main) or 49.2–50.8% (backup). Otherwise "empate técnico".
**Switch to the backup:** if the main system prints no projection line for 10 minutes after the gate opened, or
crashes. Note the time of the switch; every post from then on says "sistema reserva".

## Day before (24/10)
- [ ] Windows: set sleep to **Never** while plugged in (Settings → System → Power). Check at least 5 GB free.
- [ ] Pre-flight run: `.venv\Scripts\python -m tally live --election 6258 --once --project`. On 2026-10-20 this read
      all 85 fixed files with no error and printed "below 2.0% counted".
- [ ] Colab: open the notebook once, set `ELECTION="6258"`, run up to the base cell (cached on Drive), and stop.
- [ ] Helpers: they did the manual (`didatico/MANUAL_COLAB.md`), and the Drive shortcut works.
- [ ] Draft the first post (text plus card placeholder), so that only the numbers change at 17:30.

## Election night
| BRT | Action |
|---|---|
| 16:30 | Colab (author and helpers): open the notebook, `ELECTION="6258"`, run every cell up to the loop. |
| 16:45 | Desktop terminal 1: `.venv\Scripts\python -m tally live --election 6258 --project --until 21:00` |
| 16:45 | Desktop terminal 2: `.venv\Scripts\python tools\card_local.py --election 6258 --every 5` (cards in `reports/cards_local/`) |
| 16:50 | Start the Colab loops. |
| 17:00 | Polls close. Abroad results arrive at about 17:08. Lines say "preliminary" until the gate opens. |
| ~17:30 | Gate opens: first projection. Compare main and backup; if they differ by more than 1 pp, check the logs before posting. |
| 17:30–19:00 | Post the main card every 15–30 min, or when the call changes. |
| ~20:00 | 99% counted. Final card. Leave the collector running until 21:00 for the audit archive. |

**Post wording:** always "projeção estatística independente, NÃO é resultado oficial". Never post a helper card.

## If something fails
- **HTTP 429 or "recuo" lines:** both systems slow down by themselves. Do not start extra collectors.
- **The main collector crashed:** run the same command again. The archive is append-only, so nothing is lost.
- **Colab disconnected:** reconnect and run all cells again. The state on Drive survives.
- **Main and backup disagree by more than the two intervals:** post nothing and check `fetch_log.jsonl` status
  counts (Colab diagnostics cell; desktop `[live]` lines).

## After the night
1. Back up `data/live/ele2026_e006258/` (archive + `projections.jsonl`) and the Colab Drive folder.
2. Evaluate as pre-registered (§4): error at the first cycle after 2, 3, 5, 10, 20 and 50% counted, against the
   official final share, for both systems. Report failures as failures.
3. When TSE publishes the round-2 bweb files: `tally fetch/build` for 2026 t2, then the frozen audit (H1r2–H5r2).
4. Reveal phase 2: publish the projection pre-registration and its code; check them against the hashes in FINDINGS.
