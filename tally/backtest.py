"""Replays a run-off count in real TSE arrival order and scores the projection at each checkpoint."""

import json
import time
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import INTERIM_DIR, REPORTS_DIR, __version__  # noqa: E402
from . import project  # noqa: E402
from .config import analysis  # noqa: E402

CHECKPOINTS = [0.005, 0.01, 0.02, 0.03, 0.05, 0.10, 0.20, 0.50]
# Chosen on the 2022 backtest (FINDINGS P2), so they are tuned in-sample: validate out of sample before trusting.
MUNICIPAL_PRIOR = 500
MUNICIPAL_MIN_FRAC_CORR = 0.5


def run_cross(base: tuple[int, int], target: tuple[int, int], nr_a: str, nr_b: str, log=print) -> str:
    """Out-of-sample check of the frozen municipal configuration on a different election pair, e.g. the
    2026 round-1 count projected from the 2022 round-1 sections.
    Metric: candidate A's share of A+B votes. Sections are matched by (UF, municipality, zone, section)."""
    r1 = pd.read_parquet(INTERIM_DIR / f"sections_{base[0]}_t{base[1]}.parquet")
    r2 = pd.read_parquet(INTERIM_DIR / f"sections_{target[0]}_t{target[1]}.parquet")
    df = project.merge_rounds(r1, r2, nr_a, nr_b)
    df = df[df["DT_BU_RECEBIDO_BRT"].notna()].sort_values("DT_BU_RECEBIDO_BRT", kind="stable").reset_index(drop=True)
    truth = 100 * df["A2"].sum() / (df["A2"].sum() + df["B2"].sum())
    log(f"[cross] {base}->{target}: {len(df):,} sections, {df['matched'].mean():.2%} matched; truth A/(A+B) = {truth:.3f}%")
    p = project.Params(bootstrap=0)
    pm = project.Params(bootstrap=0, neutral_prior_sections=MUNICIPAL_PRIOR)
    rows = []
    for cp in CHECKPOINTS:
        mask = np.arange(len(df)) < int(round(cp * len(df)))
        sec = project.predict(df, mask, p)
        mun = project.predict_municipal(df, mask, pm, min_frac_corr=MUNICIPAL_MIN_FRAC_CORR)
        naive = project.predict_municipal(df, mask, p)
        ident = project.predict_municipal(df, mask, p, proxy="exact")
        sw_p = project.predict_municipal(df, mask, p, model="swing")
        sw_x = project.predict_municipal(df, mask, p, proxy="exact", model="swing")
        r = {"pct_counted": 100 * cp, "time_brt": f"{df.loc[mask, 'DT_BU_RECEBIDO_BRT'].max():%H:%M:%S}",
             "raw": project.raw_share(df, mask) - truth, "section": sec["share_a"] - truth,
             "municipal_identified": ident["share_a"] - truth,
             "municipal": mun["share_a"] - truth, "municipal_naive": naive["share_a"] - truth,
             "swing_proportional": sw_p["share_a"] - truth, "swing_identified": sw_x["share_a"] - truth}
        rows.append(r)
        log(f"[cross] {r['pct_counted']:5.1f}% ({r['time_brt']}): section {r['section']:+.3f} | transfer: "
            f"naive {r['municipal_naive']:+.3f} ident {r['municipal_identified']:+.3f} | SWING: proportional "
            f"{r['swing_proportional']:+.3f} identified {r['swing_identified']:+.3f} pp")
    out = REPORTS_DIR / f"cross_{base[0]}t{base[1]}_to_{target[0]}t{target[1]}_{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir(parents=True)
    pd.DataFrame(rows).assign(truth_a=truth, matched=df["matched"].mean()).to_csv(out / "cross.csv", index=False)
    log(f"[ok] -> {out}")
    return str(out)


def run_municipal(year: int, log=print) -> str:
    """Same replay, but the model only sees what TSE publishes live: per-municipality aggregates (FINDINGS E3)."""
    cand = analysis()["candidates"][str(year)]
    r1 = pd.read_parquet(INTERIM_DIR / f"sections_{year}_t1.parquet")
    r2 = pd.read_parquet(INTERIM_DIR / f"sections_{year}_t2.parquet")
    df = project.merge_rounds(r1, r2, cand["A"]["nr"], cand["B"]["nr"])
    df = df[df["DT_BU_RECEBIDO_BRT"].notna()].sort_values("DT_BU_RECEBIDO_BRT", kind="stable").reset_index(drop=True)
    truth = 100 * df["A2"].sum() / (df["A2"].sum() + df["B2"].sum())
    p = project.Params(bootstrap=0)
    pm = project.Params(bootstrap=0, neutral_prior_sections=MUNICIPAL_PRIOR)
    rows = []
    for cp in CHECKPOINTS:
        mask = np.arange(len(df)) < int(round(cp * len(df)))
        sec = project.predict(df, mask, p)
        mun = project.predict_municipal(df, mask, pm, min_frac_corr=MUNICIPAL_MIN_FRAC_CORR)
        prop = project.predict_municipal(df, mask, p)
        rows.append({"pct_counted": 100 * cp, "time_brt": f"{df.loc[mask, 'DT_BU_RECEBIDO_BRT'].max():%H:%M:%S}",
                     "raw_share_a": project.raw_share(df, mask), "section_model_a": sec["share_a"],
                     "municipal_model_a": mun["share_a"], "municipal_naive_a": prop["share_a"], "truth_a": truth,
                     "err_municipal_prop": prop["share_a"] - truth,
                     "err_section": sec["share_a"] - truth, "err_municipal": mun["share_a"] - truth,
                     "municipalities_started": mun["municipalities_started"],
                     "municipalities_partial": mun["municipalities_partial"],
                     "others_to_A": float(mun["beta_BR_A"][2]), "others_to_B": float(mun["beta_BR_B"][2])})
        r = rows[-1]
        log(f"[bt-mun] {r['pct_counted']:5.1f}% ({r['time_brt']}): section model {r['err_section']:+.3f} | municipal "
            f"municipal {r['err_municipal']:+.3f} (naive {r['err_municipal_prop']:+.3f}) pp | {r['municipalities_started']} municipalities "
            f"({r['municipalities_partial']} partial) | others->A {r['others_to_A']:.2f} ->B {r['others_to_B']:.2f}")
    out = REPORTS_DIR / f"backtest_{year}_t2_municipal_{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(out / "backtest_municipal.csv", index=False)
    log(f"[ok] -> {out}")
    return str(out)


def run(year: int, bootstrap: int = 50, log=print) -> str:
    cand = analysis()["candidates"][str(year)]
    nr_a, nr_b = cand["A"]["nr"], cand["B"]["nr"]
    r1 = pd.read_parquet(INTERIM_DIR / f"sections_{year}_t1.parquet")
    r2 = pd.read_parquet(INTERIM_DIR / f"sections_{year}_t2.parquet")
    df = project.merge_rounds(r1, r2, nr_a, nr_b)
    df = df[df["DT_BU_RECEBIDO_BRT"].notna()].sort_values("DT_BU_RECEBIDO_BRT", kind="stable").reset_index(drop=True)
    truth = 100 * df["A2"].sum() / (df["A2"].sum() + df["B2"].sum())
    log(f"[bt] {len(df):,} sections, {df['matched'].mean():.2%} matched to round 1; final share A = {truth:.3f}%")

    p = project.Params(bootstrap=bootstrap)
    full = project.predict(df, np.ones(len(df), bool), p)
    rows = []
    for cp in CHECKPOINTS:
        t0 = time.time()
        mask = np.arange(len(df)) < int(round(cp * len(df)))
        res = project.project(df, mask, p)
        row = {
            "pct_counted": 100 * cp,
            "time_brt": f"{df.loc[mask, 'DT_BU_RECEBIDO_BRT'].max():%H:%M:%S}",
            "ufs_counted": int(df.loc[mask, "SG_UF"].nunique()),
            "raw_share_a": project.raw_share(df, mask),
            "uniform_swing_a": project.uniform_swing(df, mask),
            "model_share_a": res["share_a"], "lo90": res["share_a_lo90"], "hi90": res["share_a_hi90"],
            "truth_a": truth,
        }
        for k in ("raw_share_a", "uniform_swing_a", "model_share_a"):
            row["err_" + k] = row[k] - truth
        row["covered"] = bool(res["share_a_lo90"] <= truth <= res["share_a_hi90"])
        for g, ba, bb in zip(project.GROUPS, res["beta_BR_A"], res["beta_BR_B"]):
            row[f"beta_{g}_to_A"], row[f"beta_{g}_to_B"] = float(ba), float(bb)
        rows.append(row)
        log(f"[bt] {100 * cp:5.1f}% ({row['time_brt']}): raw {row['err_raw_share_a']:+.2f} | swing "
            f"{row['err_uniform_swing_a']:+.2f} | model {row['err_model_share_a']:+.3f} pp "
            f"[{row['lo90']:.2f}, {row['hi90']:.2f}] covered={row['covered']} ({time.time() - t0:.0f}s)")

    out = REPORTS_DIR / f"backtest_{year}_t2_{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir(parents=True)
    tab = pd.DataFrame(rows)
    tab.to_csv(out / "backtest.csv", index=False)
    full_beta = {g: {"to_A": float(a), "to_B": float(b)}
                 for g, a, b in zip(project.GROUPS, full["beta_BR_A"], full["beta_BR_B"])}
    (out / "summary.json").write_text(json.dumps({
        "tool_version": __version__, "year": year, "truth_share_a": truth, "sections": len(df),
        "matched": float(df["matched"].mean()), "params": vars(p), "full_data_transfer_BR": full_beta,
        "checkpoints": rows}, indent=2, default=str), encoding="utf-8")
    _plot(tab, cand, out / "backtest.png")
    log(f"[ok] backtest -> {out}")
    return str(out)


def _plot(t: pd.DataFrame, cand: dict, path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    x = t["pct_counted"]
    ax.plot(x, t["raw_share_a"], "o-", color="#9aa5b1", label="raw partial count")
    ax.plot(x, t["uniform_swing_a"], "s-", color="#e0a030", label="uniform swing (naive)")
    ax.fill_between(x, t["lo90"], t["hi90"], color="#1f4e9c", alpha=0.18, lw=0, label="model 90% interval")
    ax.plot(x, t["model_share_a"], "o-", color="#1f4e9c", label="model projection")
    ax.axhline(t["truth_a"].iloc[0], color="black", lw=1, ls="--", label="final result")
    ax.set_xscale("log")
    ax.set_xticks(x, [f"{v:g}%" for v in x])
    ax.set_xlabel("sections counted, in real arrival order")
    ax.set_ylabel(f"{cand['A']['name']} share of valid votes (%)")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
