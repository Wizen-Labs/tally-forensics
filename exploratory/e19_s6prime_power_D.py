"""E19: power of S6' (deviation 01) on real data, half D round 2, after the sealed run (does not change the rule).

Adds a trigger to the real D round-2 minutes: in N random boxes open at minute M (interior), k extra votes at M.
k = 3 for A (a peak needs 3 votes in the box-minute; the injected votes are on top of the real ones), k = 1 for
B1/B2. M random between 10:00 and 15:59 BRT; 10 trials per N. Reports the share of trials where M (B2: its bin) is
flagged.

    .venv/Scripts/python exploratory/e19_s6prime_power_D.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tally import s6prime as s6
from e15_s1_s6 import TRAILS, box_table

OUT = Path(__file__).resolve().parents[1] / "reports" / "h8r2" / "s6prime" / "power_D_r2.csv"


def main() -> None:
    b, _ = box_table()
    b = b[(b["half"] == "D") & ~b["excl_all"]]
    off = b.set_index("box")["tz_offset_h"]
    v = pd.concat([pd.read_parquet(TRAILS / f"{uf}_r2.parquet", columns=["box", "t_computed"])
                   for uf in sorted(b["uf"].unique())], ignore_index=True)
    v = v[v["box"].isin(set(b["box"]))]
    d, e = s6.minutes(v, off)
    del v
    span = d.groupby("box")["minute"].agg(["min", "max"])
    rng = np.random.default_rng(20261027)
    rows = []
    for stat, k, ns in (("A", 3, [5, 10, 20, 40, 80]), ("B1", 1, [500, 1000, 2000, 4000, 8000]),
                        ("B2", 1, [500, 1000, 2000, 4000, 8000])):
        for n in ns:
            hit = 0
            for _ in range(10):
                m = int(rng.integers(10 * 60, 16 * 60))
                open_ = span.index[(span["min"] <= m) & (span["max"] >= m)].to_numpy()
                boxes = rng.choice(open_, n, replace=False)
                add = pd.DataFrame({"box": np.repeat(boxes, k), "minute": m})
                dd = pd.concat([d, add], ignore_index=True)
                if stat == "A":
                    x = s6.stat_a(dd, e)
                    hit += m in x.loc[x["flag"], "minute"].tolist()
                else:
                    w = 1 if stat == "B1" else 2
                    x = s6.stat_b(dd, e, w)
                    hit += (m // w) * w in x.loc[x["flag"], "minute"].tolist()
            rows.append({"stat": stat, "k": k, "boxes": n, "detected": hit / 10})
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)


if __name__ == "__main__":
    main()
