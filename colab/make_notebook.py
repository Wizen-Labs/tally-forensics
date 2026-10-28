"""Builds colab/tally_live_independent.ipynb from colab/tally_colab.py (single source for the module code)."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
module = (HERE / "tally_colab.py").read_text(encoding="utf-8")


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(keepends=True)}


cells = [
    md("""
# tally-forensics: independent live system (Google Colab)

A second, independent collector and projector for the 2026 presidential run-off, used as a backup and as a second
opinion to the main system.
- **Base:** the round-1 results per municipality, from TSE's own result files.
- **Model:** municipal swing on the two-party share.
- **Storage:** everything on Google Drive.

**Run order**
1. Run cells 1–4 any day before the election (access test, base build, dry run).
2. On 25 Oct, from about 16:55 BRT, set `ELECTION = "6258"` and run cell 5. Keep this tab open.

**Helpers** (trusted backups on other networks): set `HELPER_NAME` in cell 0. The notebook then polls every 90 s
with fewer connections, writes to `helpers/<name>/` inside the shared folder, and marks every card
"BACKUP · NÃO PUBLICAR". Before the first run, a helper opens the folder Eduardo shared ("Shared with me"), chooses
"Organise > Add shortcut" and puts the shortcut in "My Drive", so `SHARED_DIR` below exists in their Colab.

A Colab session drops after about 90 minutes without interaction. Click inside the notebook from time to time.
"""),
    code("""
# 0. Settings
ELECTION = "6257"          # "6257" = 2026 round 1 (test, files are final); "6258" = round 2 on 25 Oct
BASE_ELECTION = "6257"     # round 1 is the base for the run-off
NR_A, NR_B = "22", "13"    # Flavio Bolsonaro, Lula
INTERVAL_S = 30
CARD_EVERY_MIN = 5         # the live loop saves a media card to Drive every N minutes once the projection is ready
STOP_AT_BRT = "21:00"
HELPER_NAME = ""           # "" = Eduardo (main run). Helpers: your first name, e.g. "pedro" (lower case, no spaces)
SHARED_DIR = "/content/drive/MyDrive/tally_live_independent"   # helpers: the shortcut to Eduardo's shared folder

WORKERS, MAX_RPS, MAX_MUN = 16, 15, 900   # TSE answers 429 to bursts: at most 15 requests/s, 900 municipalities/cycle
if HELPER_NAME:                       # backup mode: lighter on TSE's servers, cards never for publication
    INTERVAL_S, WORKERS, CARD_EVERY_MIN, MAX_RPS, MAX_MUN = 90, 8, 15, 8, 450
    DRIVE_DIR = f"{SHARED_DIR}/helpers/{HELPER_NAME}"
    WATERMARK = "BACKUP · NÃO PUBLICAR"
else:
    DRIVE_DIR = SHARED_DIR
    WATERMARK = None if ELECTION == "6258" else "SIMULAÇÃO"
print("writing to", DRIVE_DIR, "| every", INTERVAL_S, "s |", WORKERS, "connections | max", MAX_RPS, "req/s |",
      MAX_MUN, "municipalities/cycle | watermark:", WATERMARK)
"""),
    code("""
# 1. Mount Google Drive (asks for your authorisation in a pop-up)
from google.colab import drive
drive.mount("/content/drive")
import os
os.makedirs(DRIVE_DIR, exist_ok=True)
print("storage:", DRIVE_DIR)
"""),
    code("%%writefile tally_colab.py\n" + module),
    code("""
# 2. ACCESS TEST: can Colab's servers reach TSE's results site, and how fast?
import importlib, tally_colab as tc
importlib.reload(tc)
tc.access_test("6257")
"""),
    code("""
# 3. Base: round-1 result per municipality (about 5,800 requests, ~4 min; cached on Drive afterwards)
from pathlib import Path
store = Path(DRIVE_DIR) / f"e{ELECTION}"
fetcher = tc.Fetcher(store, workers=WORKERS, max_rps=MAX_RPS)
base = tc.build_base(tc.Fetcher(Path(SHARED_DIR) / f"e{BASE_ELECTION}_base"), BASE_ELECTION, NR_A, NR_B,
                     Path(SHARED_DIR) / f"base_{BASE_ELECTION}.csv")     # helpers reuse Eduardo's cached base
print(f"{len(base):,} municipalities | A1 = {base.A1.sum():,} | B1 = {base.B1.sum():,}")
"""),
    code("""
# 4. DRY RUN on round 1 (ELECTION = "6257"): with everything counted the projection must equal the official
#    two-party share, 51.0115% for Flavio Bolsonaro.
live = tc.Live(fetcher, ELECTION, NR_A, NR_B)
print(live.cycle())
p = tc.project(live.table(), base)
print(p, "| ready:", tc.ready(p))
"""),
    code("""
# 5. LIVE LOOP (25 Oct: set ELECTION = "6258" in cell 0, re-run cells 0, 3 and this one)
import time, csv, random
from datetime import datetime
live = tc.Live(tc.Fetcher(Path(DRIVE_DIR) / f"e{ELECTION}", workers=WORKERS, max_rps=MAX_RPS), ELECTION, NR_A, NR_B,
               max_mun_per_cycle=MAX_MUN)
delay = INTERVAL_S
if HELPER_NAME:
    time.sleep(random.uniform(0, 45))    # stagger helpers so they do not hit TSE at the same second
out = Path(DRIVE_DIR) / f"projections_e{ELECTION}.csv"
cards = Path(DRIVE_DIR) / "cards"
cards.mkdir(exist_ok=True)
last_card = 0.0
new_file = not out.exists()
with open(out, "a", newline="") as fh:
    w = csv.writer(fh)
    if new_file:
        w.writerow(["t_brt", "pct_electorate_counted", "ufs_with_1pct", "raw_a", "projection_a", "ready"])
    while True:
        t0 = time.time()
        try:
            c = live.cycle()
            nat = live.national or {}
            va, vb = nat.get("votes", {}).get(NR_A, 0), nat.get("votes", {}).get(NR_B, 0)
            raw = 100 * va / max(va + vb, 1)
            p = tc.project(live.table(), base)
            ok = tc.ready(p)
            w.writerow([c["t_brt"], round(p["pct_electorate_counted"], 3), p["ufs_with_1pct"], round(raw, 3),
                        round(p["share_a"], 3), ok])
            fh.flush()
            status = (f"PROJECTION Flavio {p['share_a']:.2f}% / Lula {100 - p['share_a']:.2f}%" if ok
                      else "waiting for geographic coverage")
            print(f"{c['t_brt']} | counted {p['pct_electorate_counted']:5.2f}% | UFs>=1% {p['ufs_with_1pct']:2d} | "
                  f"raw Flavio {raw:5.2f}% | {status} | cycle {c['seconds']}s"
                  + (f" | {c['municipal_deferred']} deferred" if c['municipal_deferred'] else ""), flush=True)
            # automatic back-off: many failures -> wait longer and use fewer connections; recover when healthy
            if c["failure_rate"] > 0.2:
                delay = min(max(delay * 2, 60), 300)
                live.f.workers = max(4, live.f.workers // 2)
                print(f"   back-off: {c['failure_rate']:.0%} of requests failed (HTTP status counts {c['statuses']}) "
                      f"-> next cycle in {delay}s, {live.f.workers} connections", flush=True)
            else:
                delay, live.f.workers = INTERVAL_S, WORKERS
            if ok and c["failure_rate"] <= 0.2 and time.time() - last_card >= CARD_EVERY_MIN * 60:
                stamp = c["t_brt"][:5].replace(":", "")
                png = cards / f"card_e{ELECTION}_{stamp}.png"
                tc.make_card(out, png, half_width=0.8, watermark=WATERMARK)
                (cards / f"card_e{ELECTION}_latest.png").write_bytes(png.read_bytes())
                last_card = time.time()
                print(f"   card saved: {png.name}", flush=True)
        except Exception as e:
            delay = min(max(delay * 2, 60), 300)
            print(f"cycle error, continuing in {delay}s:", type(e).__name__, e, flush=True)
        if datetime.now(tc.BRT).strftime("%H:%M") >= STOP_AT_BRT:
            break
        time.sleep(max(1, delay - (time.time() - t0)))
"""),
    code("""
# 7. DIAGNOSTICS: HTTP status of every request in the last N minutes (200 ok, 304 not modified; 403/429 = TSE is
#    limiting this machine, 404 = file not published yet, 0 = network error or timeout)
import json, collections
from datetime import datetime, timedelta, timezone
N_MIN = 30
since = (datetime.now(timezone.utc) - timedelta(minutes=N_MIN)).isoformat()
cnt, bad = collections.Counter(), 0
for line in open(Path(DRIVE_DIR) / f"e{ELECTION}" / "fetch_log.jsonl", encoding="utf-8", errors="replace"):
    try:
        e = json.loads(line)
    except json.JSONDecodeError:
        bad += 1          # lines mixed up by parallel writes in notebook versions before 13 Oct; skipped
        continue
    if e.get("t_utc", "") >= since:
        cnt[(e.get("status"), e.get("error", "")[:60])] += 1
for (status, err), k in cnt.most_common():
    print(f"{k:7d}  status {status}  {err}")
print(f"(skipped {bad} damaged log lines)")
"""),
    code("""
# 6. MEDIA CARD (1080x1350 PNG, for social media and press). Re-run at any time during the count: it reads the
#    projection log on Drive, shows the card here and saves it to Drive. On the test election (6257) it carries
#    a "SIMULACAO" watermark. A winner is shown only when the whole +/-0.8 pp interval (FINDINGS P11) is on one side of 50%.
from IPython.display import Image, display
card = Path(DRIVE_DIR) / f"card_e{ELECTION}.png"
tc.make_card(Path(DRIVE_DIR) / f"projections_e{ELECTION}.csv", card, half_width=0.8, watermark=WATERMARK)
display(Image(filename=str(card)))
print("saved to", card)
"""),
]

nb = {"cells": cells, "metadata": {"colab": {"provenance": []}, "kernelspec": {"name": "python3",
      "display_name": "Python 3"}, "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 0}
(HERE / "tally_live_independent.ipynb").write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print("written", HERE / "tally_live_independent.ipynb", len(cells), "cells")
