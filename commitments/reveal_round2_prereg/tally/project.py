"""Live projection of a presidential run-off from the first sections counted.

Model (per UF, partially pooled UF -> region -> Brazil):
    votes_A2_i = X_i . beta_A        votes_B2_i = X_i . beta_B
where X_i = round-1 counts of the same section: [A1, B1, others1, blank+null1, abstention1]. beta is a transfer
matrix (share of each round-1 group that votes A or B in round 2), bounded to [0, 1] and fitted on the sections
counted so far (ecological regression). A UF with few counted sections borrows from its region, a region from
Brazil, through prior pseudo-observations. Remaining local deviations are corrected per municipality with
shrinkage. Uncounted sections get X_i . beta (times the municipal correction); counted sections keep their result.

Uncertainty: bootstrap over counted polling locations.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import lsq_linear

SEC = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
GROUPS = ["A1", "B1", "O1", "N1", "X1"]
REGION = {
    "AC": "N", "AM": "N", "AP": "N", "PA": "N", "RO": "N", "RR": "N", "TO": "N",
    "AL": "NE", "BA": "NE", "CE": "NE", "MA": "NE", "PB": "NE", "PE": "NE", "PI": "NE", "RN": "NE", "SE": "NE",
    "DF": "CO", "GO": "CO", "MS": "CO", "MT": "CO",
    "ES": "SE", "MG": "SE", "RJ": "SE", "SP": "SE",
    "PR": "S", "RS": "S", "SC": "S",
    "ZZ": "ZZ",
}


@dataclass
class Params:
    prior_sections: float = 200.0     # strength of the parent prior, in pseudo-sections
    muni_shrink_sections: float = 5.0  # shrinkage of the municipal correction, in sections
    bootstrap: int = 100
    seed: int = 20261025
    # Weak, candidate-symmetric prior on the national transfer matrix (A1, B1, O1, N1, X1). It only matters when
    # the data cannot identify the matrix (few, similar aggregates); it never favours either candidate.
    neutral_prior_sections: float = 0.0
    neutral_prior_own: float = 0.97
    neutral_prior_other: float = 0.01
    neutral_prior_minor: float = 0.40
    neutral_prior_blank: float = 0.15
    neutral_prior_abst: float = 0.03

    def neutral_prior(self, target: str) -> np.ndarray:
        own, other = self.neutral_prior_own, self.neutral_prior_other
        a1, b1 = (own, other) if target == "A2" else (other, own)
        return np.array([a1, b1, self.neutral_prior_minor, self.neutral_prior_blank, self.neutral_prior_abst])


def _valid_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("v_") and c[2:].isdigit()]


def round1_groups(r1: pd.DataFrame, nr_a: str, nr_b: str) -> pd.DataFrame:
    """Per-section base composition: A1, B1, others, blank+null, abstention (plus keys and aptos)."""
    v1 = _valid_cols(r1)
    blank_null = [c for c in ("v_blank", "v_null", "v_annulled") if c in r1.columns]
    x = pd.DataFrame({
        "A1": r1["v_" + nr_a], "B1": r1["v_" + nr_b],
        "O1": r1[v1].sum(axis=1) - r1["v_" + nr_a] - r1["v_" + nr_b],
        "N1": r1[blank_null].sum(axis=1),
        "X1": r1["QT_APTOS"] - r1["QT_COMPARECIMENTO"],
    })
    x[SEC] = r1[SEC]
    x["QT_APTOS_R1"] = r1["QT_APTOS"]
    return x


def merge_rounds(r1: pd.DataFrame, r2: pd.DataFrame, nr_a: str, nr_b: str) -> pd.DataFrame:
    """One row per round-2 section with its round-1 composition (X) and round-2 outcome (Y)."""
    x = round1_groups(r1, nr_a, nr_b).drop(columns="QT_APTOS_R1")
    x["R1_RECEBIDO"] = r1["DT_BU_RECEBIDO_BRT"]
    y = r2[SEC + ["NR_LOCAL_VOTACAO", "QT_APTOS", "DT_BU_RECEBIDO_BRT"]].copy()
    y["A2"] = r2["v_" + nr_a]
    y["B2"] = r2["v_" + nr_b]
    m = y.merge(x, on=SEC, how="left", validate="one_to_one")
    m["region"] = m["SG_UF"].map(REGION)
    m["matched"] = m[GROUPS].notna().all(axis=1)
    return m


def _fit(X: np.ndarray, y: np.ndarray, prior: np.ndarray | None, weight: float) -> np.ndarray:
    """Bounded least squares with an optional ridge pull towards prior (weight in pseudo-sections)."""
    if prior is not None and weight > 0:
        scale = np.sqrt(weight * np.mean(X ** 2, axis=0)) if len(X) else np.sqrt(weight) * np.ones(X.shape[1])
        X = np.vstack([X, np.diag(scale)])
        y = np.concatenate([y, scale * prior])
    if len(X) == 0:
        return prior
    return lsq_linear(X, y, bounds=(0, 1), method="bvls").x


def fit_hierarchy(counted: pd.DataFrame, target: str, p: Params) -> dict:
    """beta per level: {'BR': b, region: b, uf: b}."""
    cols = GROUPS
    prior = p.neutral_prior(target) if p.neutral_prior_sections > 0 else None
    betas = {"BR": _fit(counted[cols].to_numpy(float), counted[target].to_numpy(float), prior,
                        p.neutral_prior_sections)}
    for reg, g in counted.groupby("region"):
        betas[reg] = _fit(g[cols].to_numpy(float), g[target].to_numpy(float), betas["BR"], p.prior_sections)
    for uf, g in counted.groupby("SG_UF"):
        parent = betas.get(REGION[uf], betas["BR"])
        betas[uf] = _fit(g[cols].to_numpy(float), g[target].to_numpy(float), parent, p.prior_sections)
    return betas


def _beta_for(uf: str, betas: dict) -> np.ndarray:
    return betas.get(uf, betas.get(REGION.get(uf, ""), betas["BR"]))


def predict(df: pd.DataFrame, counted_mask: np.ndarray, p: Params) -> dict:
    """Projected national totals for A and B given which sections are counted."""
    m = df[df["matched"]]
    cm = counted_mask[df["matched"].to_numpy()]
    counted, todo = m[cm], m[~cm]
    out = {}
    for t in ("A2", "B2"):
        betas = fit_hierarchy(counted, t, p)
        uf_beta = np.vstack([_beta_for(u, betas) for u in m["SG_UF"]])
        pred = np.einsum("ij,ij->i", m[GROUPS].to_numpy(float), uf_beta)
        pred_s = pd.Series(pred, index=m.index)
        # municipal correction from counted sections, shrunk towards 1
        mun = ["SG_UF", "CD_MUNICIPIO"]
        obs_c = counted.groupby(mun)[t].sum()
        pred_c = pred_s[counted.index].groupby([counted[k] for k in mun]).sum()
        k = p.muni_shrink_sections * max(np.median(pred), 1.0)
        corr = ((obs_c + k) / (pred_c + k)).rename("corr")
        c = m[mun].join(corr, on=mun)["corr"].fillna(1.0)
        todo_pred = (pred_s * c)[todo.index].sum()
        matched_total = counted[t].sum() + todo_pred
        # unmatched sections (new in round 2): counted ones as observed, the rest by UF votes-per-eligible
        un = df[~df["matched"]]
        un_c = counted_mask[~df["matched"].to_numpy()]
        per_apto = matched_total / max(m["QT_APTOS"].sum(), 1)
        out[t] = float(matched_total + un[t][un_c].sum() + per_apto * un["QT_APTOS"][~un_c].sum())
        if t == "A2":
            out["beta_BR_A"] = betas["BR"]
        else:
            out["beta_BR_B"] = betas["BR"]
    out["share_a"] = 100 * out["A2"] / (out["A2"] + out["B2"])
    return out


def project(df: pd.DataFrame, counted_mask: np.ndarray, p: Params) -> dict:
    """Point projection plus a bootstrap interval over counted polling locations."""
    point = predict(df, counted_mask, p)
    rng = np.random.default_rng(p.seed)
    loc = df.groupby(["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"], sort=False).ngroup().to_numpy()
    counted_locs = np.unique(loc[counted_mask])
    shares = []
    for _ in range(p.bootstrap):
        pick = rng.choice(counted_locs, size=len(counted_locs), replace=True)
        mult = np.bincount(pick, minlength=loc.max() + 1)[loc]
        rows = np.repeat(np.arange(len(df)), np.where(counted_mask, mult, 1))
        boot = df.iloc[rows].reset_index(drop=True)
        mask = np.repeat(counted_mask, np.where(counted_mask, mult, 1))
        # duplicated uncounted rows are not created (mult applies to counted only), so totals stay comparable
        shares.append(predict(boot, mask, p)["share_a"])
    lo, hi = np.percentile(shares, [5, 95]) if shares else (np.nan, np.nan)
    return {**point, "share_a_lo90": float(lo), "share_a_hi90": float(hi)}


def predict_municipal(df: pd.DataFrame, counted_mask: np.ndarray, p: Params, proxy: str = "proportional",
                      min_frac_fit: float = 0.0, min_frac_corr: float = 0.0, model: str = "transfer") -> dict:
    """Projection with the information TSE actually publishes live (FINDINGS E3).

    During the count TSE publishes, per municipality, the votes and the NUMBER of sections counted, but not WHICH
    sections. The counted part's round-1 composition is approximated by `proxy`:
    - "proportional": municipal round-1 totals times the share of the electorate counted;
    - "r1_order": the municipality's first n sections in round-1 arrival order (same boxes, same transmission
      points), where n is the published count. Exact once the municipality is complete. Tested on 2022 and
      found WORSE than proportional (FINDINGS P2); kept only for the record.
    - "exact": the sections actually counted. This is the live best case IF TSE's section files reveal which
      sections are totalised (FINDINGS E3): municipal votes, but exact round-1 composition of the counted part.
    min_frac_fit: fit the transfer matrix only on municipalities at least this complete (falls back to all
    started municipalities when fewer than 30 qualify); the municipal correction uses the same threshold.
    """
    m = df[df["matched"]].copy()
    cm = counted_mask[df["matched"].to_numpy()]
    mun = ["SG_UF", "CD_MUNICIPIO"]
    if proxy == "r1_order":
        n_counted = pd.Series(cm.astype(int), index=m.index).groupby([m[k] for k in mun]).transform("sum")
        r1_rank = m.groupby(mun)["R1_RECEBIDO"].rank(method="first")
        part = m.loc[(r1_rank <= n_counted).to_numpy()].groupby(mun)[GROUPS].sum()
    elif proxy == "exact":
        part = m.loc[cm].groupby(mun)[GROUPS].sum()
    m["A2c"] = np.where(cm, m["A2"], 0)
    m["B2c"] = np.where(cm, m["B2"], 0)
    m["apt_c"] = np.where(cm, m["QT_APTOS"], 0)
    m["n_c"] = cm.astype(int)
    agg = m.groupby(mun).agg(**{g: (g, "sum") for g in GROUPS}, apt=("QT_APTOS", "sum"), n=("QT_APTOS", "size"),
                             apt_c=("apt_c", "sum"), n_c=("n_c", "sum"), A2c=("A2c", "sum"), B2c=("B2c", "sum"))
    agg = agg.reset_index()
    agg["frac"] = (agg["apt_c"] / agg["apt"]).where(agg["n_c"] < agg["n"], 1.0).fillna(0)
    if proxy in ("r1_order", "exact"):
        Xc = part.reindex(pd.MultiIndex.from_frame(agg[mun])).fillna(0).to_numpy(float)
    else:
        Xc = agg[GROUPS].to_numpy(float) * agg[["frac"]].to_numpy()
    unmatched = {t: float(df.loc[~df["matched"], t].sum()) for t in ("A2", "B2")}   # rare; taken as observed
    if model == "swing":
        return project_swing(agg, Xc, extra=unmatched)
    return project_aggregates(agg, Xc, p, min_frac_fit, min_frac_corr, unmatched)


def project_aggregates(agg: pd.DataFrame, Xc: np.ndarray, p: Params, min_frac_fit: float = 0.0,
                       min_frac_corr: float = 0.0, extra: dict | None = None) -> dict:
    """Core municipal projection, shared by the backtest and the live collector.

    agg: one row per municipality with SG_UF, the round-1 groups (full municipality), n (sections), frac (share of the
    municipality counted, 1.0 when complete) and the counted votes A2c, B2c. Xc: round-1 groups of the counted part.
    """
    agg = agg.copy()
    agg["region"] = agg["SG_UF"].map(REGION)
    X = agg[GROUPS].to_numpy(float)
    extra = extra or {}
    started = agg[agg["frac"] > 0].copy()
    started[GROUPS] = Xc[agg["frac"].to_numpy() > 0]
    if min_frac_fit > 0 and (started["frac"] >= min_frac_fit).sum() >= 30:
        started = started[started["frac"] >= min_frac_fit]
    use_corr = agg["frac"].to_numpy() >= max(min_frac_fit, min_frac_corr, 1e-12)
    out = {}
    for t, obs in (("A2", "A2c"), ("B2", "B2c")):
        fit_rows = started.rename(columns={obs: t})
        betas = fit_hierarchy(fit_rows, t, p)
        beta = np.vstack([_beta_for(u, betas) for u in agg["SG_UF"]])
        pred_full = np.einsum("ij,ij->i", X, beta)
        pred_counted = np.einsum("ij,ij->i", Xc, beta)
        per_section = np.median(pred_full / agg["n"].clip(lower=1))
        k = p.muni_shrink_sections * max(per_section, 1.0)
        corr = (agg[obs].to_numpy() + k) / (pred_counted + k)
        corr = np.where(use_corr, corr, 1.0)
        remainder = (pred_full - pred_counted) * corr
        out[t] = float(agg[obs].sum() + remainder.sum() + extra.get(t, 0.0))
        out[f"beta_BR_{t[0]}"] = betas["BR"]
    out["share_a"] = 100 * out["A2"] / (out["A2"] + out["B2"])
    out["municipalities_started"] = int((agg["frac"] > 0).sum())
    out["municipalities_partial"] = int(((agg["frac"] > 0) & (agg["frac"] < 1)).sum())
    return out


def _shrunk(num: pd.Series, den: pd.Series, parent: pd.Series, k: float) -> pd.Series:
    """(num + k * parent) / (den + k): a ratio shrunk towards its parent level."""
    return (num + k * parent) / (den + k)


def project_swing(agg: pd.DataFrame, Xc: np.ndarray, k_mun: float = 3000.0, k_uf: float = 20000.0,
                  extra: dict | None = None) -> dict:
    """Municipal swing model for municipal-level live data (a standard swing approach, implemented here independently).

    Two-party share A/(A+B). For each municipality, swing = share in the counted part now minus the base share of the
    same part (Xc), shrunk towards the UF swing, the UF towards its region, the region towards Brazil (k = votes of
    pseudo-evidence). Turnout ratio (A2+B2)/(A1+B1) is shrunk the same way. The uncounted part of each municipality
    gets base share + swing and base votes x turnout ratio.
    """
    a = agg.copy()
    a["region"] = a["SG_UF"].map(REGION)
    a["A1c"], a["B1c"] = Xc[:, 0], Xc[:, 1]
    a["V1c"] = a["A1c"] + a["B1c"]
    a["V2c"] = a["A2c"] + a["B2c"]
    a["A1r"], a["B1r"] = a["A1"] - a["A1c"], a["B1"] - a["B1c"]
    # Swing and turnout are vote-weighted: numerators in votes, denominators in base votes.
    a["sw_num"] = a["A2c"] - a["V2c"] * (a["A1c"] / a["V1c"].replace(0, np.nan)).fillna(0)
    a["tr_num"] = a["V2c"]
    levels = {}
    br = a[["sw_num", "V2c", "tr_num", "V1c"]].sum()
    br_sw = br["sw_num"] / max(br["V2c"], 1)
    br_tr = br["tr_num"] / max(br["V1c"], 1)
    g = a.groupby("region")[["sw_num", "V2c", "tr_num", "V1c"]].sum()
    reg_sw = _shrunk(g["sw_num"], g["V2c"], br_sw, k_uf)
    reg_tr = _shrunk(g["tr_num"], g["V1c"], br_tr, k_uf)
    g = a.groupby("SG_UF")[["sw_num", "V2c", "tr_num", "V1c"]].sum()
    parent_sw = a.groupby("SG_UF")["region"].first().map(reg_sw).fillna(br_sw)
    parent_tr = a.groupby("SG_UF")["region"].first().map(reg_tr).fillna(br_tr)
    uf_sw = _shrunk(g["sw_num"], g["V2c"], parent_sw, k_uf)
    uf_tr = _shrunk(g["tr_num"], g["V1c"], parent_tr, k_uf)
    p_sw = a["SG_UF"].map(uf_sw)
    p_tr = a["SG_UF"].map(uf_tr)
    sw = _shrunk(a["sw_num"], a["V2c"], p_sw, k_mun)
    tr = _shrunk(a["tr_num"], a["V1c"], p_tr, k_mun)
    v1r = (a["A1r"] + a["B1r"]).clip(lower=0)
    s1r = (a["A1r"] / v1r.replace(0, np.nan)).fillna(0.5)
    v2r = v1r * tr
    a2r = (s1r + sw).clip(0, 1) * v2r
    extra = extra or {}
    A = float(a["A2c"].sum() + a2r.sum() + extra.get("A2", 0.0))
    B = float(a["B2c"].sum() + (v2r - a2r).sum() + extra.get("B2", 0.0))
    levels["swing_BR_pp"] = 100 * br_sw
    return {"A2": A, "B2": B, "share_a": 100 * A / (A + B), **levels}


def raw_share(df: pd.DataFrame, counted_mask: np.ndarray) -> float:
    c = df[counted_mask]
    return float(100 * c["A2"].sum() / (c["A2"].sum() + c["B2"].sum()))


def uniform_swing(df: pd.DataFrame, counted_mask: np.ndarray) -> float:
    """Naive benchmark: each uncounted section repeats its round-1 A/(A+B) plus the national swing seen so far."""
    m = df[df["matched"] & ((df["A1"] + df["B1"]) > 0)]
    cm = counted_mask[(df["matched"] & ((df["A1"] + df["B1"]) > 0)).to_numpy()]
    v1 = m["A1"] + m["B1"]
    s1 = m["A1"] / v1
    c = m[cm]
    swing = c["A2"].sum() / (c["A2"] + c["B2"]).sum() - (c["A1"].sum() / (c["A1"] + c["B1"]).sum())
    todo = m[~cm]
    a = c["A2"].sum() + ((s1[~cm] + swing).clip(0, 1) * v1[~cm]).sum()
    tot = (c["A2"] + c["B2"]).sum() + v1[~cm].sum()
    return float(100 * a / tot) if len(todo) or len(c) else float("nan")
