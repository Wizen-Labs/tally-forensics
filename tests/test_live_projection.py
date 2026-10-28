import numpy as np
import pandas as pd
import pytest

from tally import live_projection as lp
from tally import project

from .test_project import _rounds

CFG = {"candidates": {"A": {"nr": "22", "name": "A"}, "B": {"nr": "13", "name": "B"}},
       "min_pct_counted": 2.0, "half_width_pp": 0.7}


def _live_state(r2: pd.DataFrame, mask: np.ndarray) -> dict:
    """What TSE would publish at this moment: per-municipality progress and counted votes, plus the national file."""
    d = r2.assign(c=mask.astype(int), apt_c=np.where(mask, r2["QT_APTOS"], 0),
                  a=np.where(mask, r2["v_22"], 0), b=np.where(mask, r2["v_13"], 0))
    g = d.groupby(["SG_UF", "CD_MUNICIPIO"]).agg(sections_total=("c", "size"), sections_counted=("c", "sum"),
                                                 electorate_total=("QT_APTOS", "sum"),
                                                 electorate_counted=("apt_c", "sum"), v_22=("a", "sum"),
                                                 v_13=("b", "sum")).reset_index()
    br = {"sections_total": len(r2), "sections_counted": int(mask.sum()),
          "votes": {"22": int(g["v_22"].sum()), "13": int(g["v_13"].sum())}, "generated": "x"}
    return {"ab": g.drop(columns=["v_22", "v_13"]), "municipal": g[["SG_UF", "CD_MUNICIPIO", "v_22", "v_13"]], "br": br}


def test_live_path_equals_backtest_path():
    r1, r2 = _rounds(seed=4)
    df = project.merge_rounds(r1, r2, "22", "13")
    order = np.argsort(df["DT_BU_RECEBIDO_BRT"].to_numpy(), kind="stable")
    mask_df = np.zeros(len(df), bool)
    mask_df[order[: int(0.05 * len(df))]] = True
    p = project.Params(bootstrap=0)
    expected = (project.predict_municipal(df, mask_df, p)["share_a"]
                + project.predict_municipal(df, mask_df, p, model="swing")["share_a"]) / 2

    key = df[["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]].astype(str).agg("|".join, axis=1)
    counted = set(key[mask_df])
    r2_key = r2[["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]].astype(str).agg("|".join, axis=1)
    state = _live_state(r2, r2_key.isin(counted).to_numpy())
    base = lp.base_by_municipality(r1, "22", "13")
    r = lp.project_live(state, base, CFG)
    assert r["status"] == "projection"
    assert r["estimate_a"] == pytest.approx(expected, abs=1e-9)
    assert r["lo"] == pytest.approx(expected - 0.7) and r["hi"] == pytest.approx(expected + 0.7)


def _with_u_progress(state: dict) -> dict:
    """Add the progress fields a municipal file carries itself (as tally.live.load_state does)."""
    ab = state["ab"]
    mun = state["municipal"].merge(ab, on=["SG_UF", "CD_MUNICIPIO"])
    mun = mun.rename(columns={"sections_counted": "u_sections_counted", "sections_total": "u_sections_total",
                              "electorate_counted": "u_electorate_counted", "electorate_total": "u_electorate_total"})
    return {**state, "municipal": mun}


def test_failed_municipal_download_counts_as_not_counted_not_as_zero_votes():
    """Regression (found in the Colab test of 2026-10-13): a municipality whose results file failed to download must
    not be treated as 'counted with zero votes'."""
    r1, r2 = _rounds(seed=6)
    base = lp.base_by_municipality(r1, "22", "13")
    full = _with_u_progress(_live_state(r2, np.ones(len(r2), bool)))
    lost = set(full["municipal"]["CD_MUNICIPIO"].unique()[:40])            # their downloads failed
    broken = {**full, "municipal": full["municipal"][~full["municipal"]["CD_MUNICIPIO"].isin(lost)]}
    uncounted = _with_u_progress(_live_state(r2, ~r2["CD_MUNICIPIO"].isin(lost).to_numpy()))
    uncounted = {**uncounted, "ab": full["ab"],
                 "municipal": uncounted["municipal"][~uncounted["municipal"]["CD_MUNICIPIO"].isin(lost)]}
    got = lp.project_live(broken, base, CFG)["estimate_a"]
    expected = lp.project_live(uncounted, base, CFG)["estimate_a"]
    assert got == pytest.approx(expected, abs=1e-9)


def test_no_projection_before_threshold_and_call_rule():
    r1, r2 = _rounds(seed=5)
    base = lp.base_by_municipality(r1, "22", "13")
    few = np.zeros(len(r2), bool)
    few[:10] = True
    assert lp.project_live(_live_state(r2, few), base, CFG)["status"].startswith("preliminary")
    full = lp.project_live(_live_state(r2, np.ones(len(r2), bool)), base, CFG)
    truth = 100 * r2["v_22"].sum() / (r2["v_22"].sum() + r2["v_13"].sum())
    assert full["estimate_a"] == pytest.approx(truth, abs=1e-6)
    assert full["call"] == ("A" if truth - 0.7 > 50 else "B" if truth + 0.7 < 50 else None)


def test_coverage_gate_waits_for_enough_ufs():
    """Owner's representativeness rule: no projection until enough UFs have 1% of their electorate counted."""
    r1, r2 = _rounds(seed=7)
    base = lp.base_by_municipality(r1, "22", "13")
    state = _live_state(r2, np.ones(len(r2), bool))
    n_ufs = r2.loc[r2["SG_UF"].str.upper() != "ZZ", "SG_UF"].nunique()
    assert lp.project_live(state, base, {**CFG, "min_ufs_with_1pct": n_ufs + 1})["status"].startswith("preliminary")
    r = lp.project_live(state, base, {**CFG, "min_ufs_with_1pct": n_ufs})
    assert r["status"] == "projection" and r["ufs_with_1pct"] == n_ufs
