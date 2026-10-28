"""P11: the Colab model (colab/tally_colab.py `project`, untouched defaults) on the same two backtests as P5.

The count is replayed in real TSE arrival order. At each checkpoint the model sees only what TSE publishes live:
per-municipality votes, sections counted and electorate counted. The base is the round-1 result per municipality.
Run: .venv\\Scripts\\python exploratory\\p11_colab_model_backtest.py
"""

import sys
from pathlib import Path

import pandas as pd

LAB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(LAB / "colab"))
sys.path.insert(0, str(LAB))
import tally_colab  # noqa: E402
from tally import INTERIM_DIR, REPORTS_DIR  # noqa: E402

CHECKPOINTS = [0.02, 0.03, 0.05, 0.10, 0.20, 0.50]
NR_A, NR_B = "22", "13"            # 2022: Bolsonaro / Lula; 2026: Flávio Bolsonaro / Lula
KEY = ["uf", "mun"]


def municipal(df: pd.DataFrame) -> pd.DataFrame:
    d = df.assign(uf=df["SG_UF"].str.lower(), mun=df["CD_MUNICIPIO"].astype(int).astype(str))
    return d


def backtest(base_file: str, target_file: str, label: str) -> pd.DataFrame:
    r1 = municipal(pd.read_parquet(INTERIM_DIR / base_file))
    base = r1.groupby(KEY).agg(A1=("v_" + NR_A, "sum"), B1=("v_" + NR_B, "sum")).reset_index()
    r2 = municipal(pd.read_parquet(INTERIM_DIR / target_file))
    r2 = r2[r2["DT_BU_RECEBIDO_BRT"].notna()].sort_values("DT_BU_RECEBIDO_BRT", kind="stable").reset_index(drop=True)
    truth = 100 * r2["v_" + NR_A].sum() / (r2["v_" + NR_A].sum() + r2["v_" + NR_B].sum())
    totals = r2.groupby(KEY).agg(ts=("QT_APTOS", "size"), te=("QT_APTOS", "sum")).reset_index()
    rows = []
    for cp in CHECKPOINTS:
        n = int(round(cp * len(r2)))
        c = r2.iloc[:n].groupby(KEY).agg(A2c=("v_" + NR_A, "sum"), B2c=("v_" + NR_B, "sum"),
                                         st=("QT_APTOS", "size"), est=("QT_APTOS", "sum")).reset_index()
        live = totals.merge(c, on=KEY, how="left").fillna({"A2c": 0, "B2c": 0, "st": 0, "est": 0})
        p = tally_colab.project(live, base)
        rows.append({"backtest": label, "pct_sections": 100 * cp,
                     "time_brt": f"{r2['DT_BU_RECEBIDO_BRT'].iloc[n - 1]:%H:%M:%S}",
                     "pct_electorate": round(p["pct_electorate_counted"], 2), "ufs_with_1pct": p["ufs_with_1pct"],
                     "ready": tally_colab.ready(p), "projection_a": round(p["share_a"], 3), "truth_a": round(truth, 3),
                     "error_pp": round(p["share_a"] - truth, 3)})
        print(rows[-1], flush=True)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    t = pd.concat([backtest("sections_2022_t1.parquet", "sections_2026_t1.parquet", "2022 r1 -> 2026 r1"),
                   backtest("sections_2022_t1.parquet", "sections_2022_t2.parquet", "2022 r1 -> 2022 r2")])
    out = REPORTS_DIR / "p11_colab_model_backtest"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "p11_colab_backtest.csv", index=False)
    print(f"max |error| = {t['error_pp'].abs().max():.3f} pp -> {out}")
