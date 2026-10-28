"""Media card from the MAIN (local) system's projections, using the same card layout as the Colab backup.

Output only: it reads `projections.jsonl` from the live archive and changes no frozen file or model. The card's header
shows the share of the electorate counted, taken from the archive's latest progress files.
Run, next to `python -m tally live --election 6258 --project`:
    .venv\\Scripts\\python tools\\card_local.py --election 6258 --every 5
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB / "colab"))
sys.path.insert(0, str(LAB))
import tally_colab  # noqa: E402
from tally import DATA_DIR, live  # noqa: E402

HALF_WIDTH = 0.7          # main system, PREREGISTRATION_ROUND2_PROJECTION.md §3


def rows(archive: Path) -> pd.DataFrame:
    out = []
    for line in open(archive / "projections.jsonl", encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        ok = r.get("status") == "projection"
        t = datetime.fromisoformat(r["t_local"]).astimezone(tally_colab.BRT)
        out.append({"day": t.date(), "t_brt": t.strftime("%H:%M:%S"), "pct_electorate_counted": r.get("pct_sections_counted", 0.0),
                    "ufs_with_1pct": r.get("ufs_with_1pct", 0), "raw_a": r.get("raw_a", 0.0),
                    "projection_a": r.get("estimate_a") if ok else None, "ready": ok})
    d = pd.DataFrame(out)
    d = d[d["day"] == d["day"].iloc[-1]].drop(columns="day").reset_index(drop=True)   # this evening only
    counting = d[d["pct_electorate_counted"] > 0]             # rows before the first result would pull the chart to 0%
    d = (counting if len(counting) else d.tail(1)).reset_index(drop=True)
    ab = live.load_state(archive)["ab"]                     # header figure: electorate counted, latest progress
    d.loc[d.index[-1], "pct_electorate_counted"] = 100 * ab["electorate_counted"].sum() / max(ab["electorate_total"].sum(), 1)
    return d


def make(election: str, out_dir: Path) -> Path:
    archive = DATA_DIR / "live" / f"{live.CYCLE}_e{election.zfill(6)}"
    d = rows(archive)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv = out_dir / f"projections_local_e{election}.csv"
    d.to_csv(csv, index=False)
    png = out_dir / f"card_local_e{election}_{d['t_brt'].iloc[-1][:5].replace(':', '')}.png"
    tally_colab.make_card(csv, png, half_width=HALF_WIDTH, watermark=None if election == "6258" else "SIMULAÇÃO")
    (out_dir / f"card_local_e{election}_latest.png").write_bytes(png.read_bytes())
    return png


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--election", default="6258")
    ap.add_argument("--every", type=float, default=0, help="minutes between cards; 0 = once")
    ap.add_argument("--out", default=str(LAB / "reports" / "cards_local"))
    a = ap.parse_args()
    while True:
        try:
            print("card:", make(a.election, Path(a.out)), flush=True)
        except Exception as e:                               # the archive may not exist yet early in the evening
            print("no card yet:", type(e).__name__, e, flush=True)
        if not a.every:
            break
        time.sleep(60 * a.every)
