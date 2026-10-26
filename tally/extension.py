"""H6r2: sections whose voting was extended past the normal close (25 Oct 2026, extension to 19:00 BRT).

Protocol: PREREGISTRATION_ROUND2_EXTENSION.md, fixed and timestamped on 2026-10-25 before TSE published the
round-2 ballot-box files. Every measure is a change within the same section between rounds, so the fixed profile of
each section cancels out; extended sections are compared with sections that closed on time.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

KEY = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
MUN = ["SG_UF", "CD_MUNICIPIO"]
METRICS = ["d_share", "d_turnout", "d_blank_null"]


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def section_changes(r1: pd.DataFrame, r2: pd.DataFrame, nr_a: str, nr_b: str, cutoff: str,
                    close_col: str = "DT_ENCERRAMENTO_BRT", min_valid: int = 30) -> pd.DataFrame:
    """One row per section present in both rounds, with the round-to-round changes and the extended flag."""
    def prep(s, tag):
        d = s[KEY + [f"v_{nr_a}", f"v_{nr_b}", "v_blank", "v_null", "QT_APTOS", "QT_COMPARECIMENTO"]].copy()
        two = d[f"v_{nr_a}"] + d[f"v_{nr_b}"]
        out = d[KEY].copy()
        out[f"share_{tag}"] = d[f"v_{nr_a}"] / two.where(two > 0)
        out[f"turnout_{tag}"] = d["QT_COMPARECIMENTO"] / d["QT_APTOS"].where(d["QT_APTOS"] > 0)
        out[f"blank_null_{tag}"] = (d["v_blank"] + d["v_null"]) / d["QT_COMPARECIMENTO"].where(
            d["QT_COMPARECIMENTO"] > 0)
        out[f"two_{tag}"] = two
        return out

    d = prep(r1, "r1").merge(prep(r2, "r2"), on=KEY).merge(r2[KEY + [close_col]], on=KEY)
    d = d[(d["two_r1"] >= min_valid) & (d["two_r2"] >= min_valid)].dropna(subset=["share_r1", "share_r2"])
    t = d[close_col]
    d["extended"] = (t.dt.hour * 60 + t.dt.minute) >= _minutes(cutoff)
    for m in ("share", "turnout", "blank_null"):
        d[f"d_{m}"] = d[f"{m}_r2"] - d[f"{m}_r1"]
    return d.reset_index(drop=True)


def _block_permutation(v: np.ndarray, lab: np.ndarray, gid: np.ndarray, permutations: int, seed: int) -> tuple:
    """Mean of the group-centred metric over labelled units; labels permuted within groups; two-sided p."""
    v = v - pd.Series(v).groupby(gid).transform("mean").to_numpy()
    obs = v[lab].mean()
    rng = np.random.default_rng(seed)
    order = np.argsort(gid, kind="stable")
    blocks = np.split(order, np.flatnonzero(np.diff(gid[order])) + 1)
    null = np.empty(permutations)
    for i in range(permutations):
        perm = lab.copy()
        for b in blocks:
            perm[b] = rng.permutation(lab[b])
        null[i] = v[perm].mean()
    return float(obs), float((1 + np.sum(np.abs(null) >= abs(obs))) / (permutations + 1))


def within_municipality(d: pd.DataFrame, metric: str, permutations: int, seed: int) -> dict:
    """H6a: extended vs on-time sections of the SAME municipality (only municipalities with both)."""
    g = d.groupby(MUN, sort=False)["extended"]
    x = d[g.transform("any") & ~g.transform("all")].dropna(subset=[metric])
    out = {"test": "H6a_within_municipality", "metric": metric, "municipalities": int(x.groupby(MUN).ngroups),
           "n_extended": int(x["extended"].sum()), "n_on_time": int((~x["extended"]).sum())}
    if out["n_extended"] == 0 or out["n_on_time"] == 0:
        return {**out, "statistic": None, "p_value": None}
    gid = x.groupby(MUN, sort=False).ngroup().to_numpy()
    stat, p = _block_permutation(x[metric].to_numpy(), x["extended"].to_numpy(), gid, permutations, seed)
    return {**out, "statistic": stat, "p_value": p}


def across_municipalities(d: pd.DataFrame, metric: str, permutations: int, seed: int, min_share: float = 0.5,
                          max_control_share: float = 0.2, deciles: int = 10) -> dict:
    """H6b: municipalities with at least min_share of sections extended vs municipalities with at most
    max_control_share extended, within strata of UF x round-1 share decile; labels permuted within strata."""
    rows = []
    for k, s in d.groupby(MUN):
        w = s["two_r2"].to_numpy()
        rows.append({"SG_UF": k[0], "CD_MUNICIPIO": k[1], "ext_share": s["extended"].mean(),
                     "share_r1": np.average(s["share_r1"], weights=s["two_r1"]),
                     metric: np.average(s[metric], weights=w) if s[metric].notna().all() else np.nan})
    m = pd.DataFrame(rows).dropna(subset=[metric])
    m["treated"] = m["ext_share"] >= min_share
    m = m[m["treated"] | (m["ext_share"] <= max_control_share)].copy()
    if not m["treated"].any() or m["treated"].all():
        return {"test": "H6b_across_municipalities", "metric": metric, "n_treated": int(m["treated"].sum()),
                "n_control": int((~m["treated"]).sum()), "strata": 0, "statistic": None, "p_value": None}
    m["dec"] = pd.qcut(m["share_r1"].rank(method="first"), deciles, labels=False)
    m["stratum"] = m["SG_UF"] + "_" + m["dec"].astype(str)
    st = m.groupby("stratum")["treated"]
    m = m[st.transform("any") & ~st.transform("all")]
    out = {"test": "H6b_across_municipalities", "metric": metric, "n_treated": int(m["treated"].sum()),
           "n_control": int((~m["treated"]).sum()), "strata": int(m["stratum"].nunique())}
    if out["n_treated"] == 0 or out["n_control"] == 0:
        return {**out, "statistic": None, "p_value": None}
    sid = m.groupby("stratum").ngroup().to_numpy()
    stat, p = _block_permutation(m[metric].to_numpy(), m["treated"].to_numpy(), sid, permutations, seed)
    return {**out, "statistic": stat, "p_value": p}


def turnout_outliers(d: pd.DataFrame, quantile: float = 0.999) -> dict:
    """H6c: extended sections whose turnout change lies beyond the two-sided `quantile` band of on-time sections
    of the same UF. Under no difference, the expected rate is 2 * (1 - quantile)."""
    flagged = []
    for uf, s in d.groupby("SG_UF"):
        ref = s.loc[~s["extended"], "d_turnout"].dropna()
        ext = s[s["extended"]].dropna(subset=["d_turnout"])
        if len(ref) < 100 or ext.empty:
            continue
        lo, hi = ref.quantile(1 - quantile), ref.quantile(quantile)
        flagged.append(ext[(ext["d_turnout"] < lo) | (ext["d_turnout"] > hi)])
    f = pd.concat(flagged) if flagged else d.iloc[0:0]
    n_ext = int(d["extended"].sum())
    expected = 2 * (1 - quantile)
    from scipy.stats import binomtest
    p = binomtest(len(f), n_ext, expected, alternative="greater").pvalue if n_ext else None
    return {"test": "H6c_turnout_outliers", "n_extended": n_ext, "n_flagged": int(len(f)),
            "expected_rate": expected, "p_value": None if p is None else float(p),
            "flagged": f[KEY + ["turnout_r1", "turnout_r2", "d_turnout"]].to_dict("records")}
