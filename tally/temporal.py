"""Temporal filter: arrival curve, residuals by reception time, and the freeze-window permutation test."""

import numpy as np
import pandas as pd

from .residuals import LOCATION, design_matrix


def window_bounds(day: pd.Timestamp, start: str, end: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    return day + pd.Timedelta(start + ":00"), day + pd.Timedelta(end + ":00")


def election_day(s: pd.DataFrame) -> pd.Timestamp:
    return s.loc[s["SG_UF"] != "ZZ", "DT_BU_RECEBIDO_BRT"].dt.normalize().mode().iloc[0]


def arrival_curve(s: pd.DataFrame, bin_minutes: int) -> pd.DataFrame:
    """Sections received per bin and the tally as it would read if published in arrival order."""
    t = s["DT_BU_RECEBIDO_BRT"].dt.floor(f"{bin_minutes}min")
    g = s.groupby(t).agg(sections=("NR_SECAO", "size"), votes_a=("votes_a", "sum"),
                         votes_b=("votes_b", "sum"), valid=("valid", "sum"))
    g = g.sort_index()
    cum = g[["sections", "votes_a", "votes_b", "valid"]].cumsum()
    g["pct_sections"] = 100 * cum["sections"] / len(s)
    g["cum_share_a"] = 100 * cum["votes_a"] / cum["valid"]
    g["cum_share_b"] = 100 * cum["votes_b"] / cum["valid"]
    g["bin_share_a"] = 100 * g["votes_a"] / g["valid"]
    g["bin_share_b"] = 100 * g["votes_b"] / g["valid"]
    return g.rename_axis("bin_start_brt")


def residuals_by_bin(s: pd.DataFrame, bin_minutes: int, metric: str, by: str | None = None,
                     min_n: int = 30) -> pd.DataFrame:
    """Mean residual per reception-time bin (optionally per UF). Cells with < min_n sections are NaN."""
    t = s["DT_BU_RECEBIDO_BRT"].dt.floor(f"{bin_minutes}min").rename("bin")
    keys = [s[by], t] if by else [t]
    g = s.groupby(keys)[metric].agg(["mean", "count"])
    g.loc[g["count"] < min_n, "mean"] = np.nan
    return g


def _within_group_permutation(groups: np.ndarray, labels: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Shuffles boolean labels within each group; groups must be sorted."""
    order = np.lexsort((rng.random(len(groups)), groups))
    return labels[order]


COVARIATES = ["close_bucket", "sec_rank_q", "log_aptos", "aggregated"]


def reception_gaps(s: pd.DataFrame, min_minutes: int = 5, until_share: float = 0.95) -> list[dict]:
    """Runs of >= min_minutes consecutive minutes with zero BU receptions nationwide (Brazil only), between the
    first reception and the moment until_share of sections had been received."""
    t = s.loc[s["SG_UF"] != "ZZ", "DT_BU_RECEBIDO_BRT"].dropna().sort_values()
    end = t.iloc[int(until_share * (len(t) - 1))]
    per_min = t.dt.floor("min").value_counts().reindex(pd.date_range(t.iloc[0].floor("min"), end.floor("min"),
                                                                     freq="min"), fill_value=0)
    gaps, start = [], None
    for ts, n in per_min.items():
        if n == 0 and start is None:
            start = ts
        elif n > 0 and start is not None:
            if (ts - start).total_seconds() / 60 >= min_minutes:
                gaps.append({"start": str(start), "end": str(ts), "minutes": int((ts - start).total_seconds() / 60)})
            start = None
    return gaps


def scan_bins(s: pd.DataFrame, bin_minutes: int, until_share: float, metric: str, permutations: int, seed: int,
              adjust: bool = True) -> pd.DataFrame:
    """Round-2 primary forensic test: the window test applied to every reception bin, from the first reception until
    until_share of sections had been received. Read with a Bonferroni threshold alpha / number of bins."""
    t = s["DT_BU_RECEBIDO_BRT"].dropna().sort_values()
    first, end = t.iloc[0].floor(f"{bin_minutes}min"), t.iloc[int(until_share * (len(t) - 1))]
    rows = []
    for start in pd.date_range(first, end, freq=f"{bin_minutes}min"):
        r = window_test(s, start, start + pd.Timedelta(minutes=bin_minutes), metric, permutations, seed, adjust)
        rows.append(r)
    return pd.DataFrame(rows)


def _adjust(d: pd.DataFrame, metric: str, loc_id: pd.Series) -> np.ndarray:
    """Removes the part of the metric explained by pre-transmission covariates, within location.

    The coefficients are fitted on out-of-window sections only, so the adjustment never sees the window it tests.
    """
    X = design_matrix(d)
    y = d[metric].to_numpy()
    lid = loc_id.to_numpy()

    def demean(a):
        a = np.asarray(a, dtype=float)
        sums = np.zeros((lid.max() + 1,) + a.shape[1:])
        np.add.at(sums, lid, a)
        counts = np.bincount(lid, minlength=lid.max() + 1).astype(float)
        means = sums / counts.reshape((-1,) + (1,) * (a.ndim - 1))
        return a - means[lid]

    Xd, yd = demean(X), demean(y)
    fit = ~d["inside"].to_numpy()
    beta, *_ = np.linalg.lstsq(Xd[fit], yd[fit], rcond=None)
    return y - X @ beta


def window_test(s: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, metric: str,
                permutations: int, seed: int, adjust: bool = False) -> dict:
    """Do sections received inside [start, end) differ from their own polling-location siblings received outside?

    Only locations with sections both inside and outside the window are informative. The window labels are
    permuted within each location, which keeps every location's composition fixed, so the null distribution
    already absorbs geography, location size and over-dispersion. With adjust=True the metric is first
    corrected for pre-transmission covariates (close delay, section rank, size, aggregation).
    """
    cols = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO", "DT_BU_RECEBIDO_BRT", metric]
    d = s[cols + (COVARIATES if adjust else [])].dropna()
    d = d.assign(inside=(d["DT_BU_RECEBIDO_BRT"] >= start) & (d["DT_BU_RECEBIDO_BRT"] < end))
    loc_id = d.groupby(LOCATION, sort=False).ngroup()
    by_loc = d["inside"].groupby(loc_id)
    mixed = by_loc.transform("any") & ~by_loc.transform("all")
    d = d[mixed]
    loc_id = d.groupby(LOCATION, sort=False).ngroup()
    if adjust and len(d):
        d = d.assign(**{metric: _adjust(d, metric, loc_id)})

    result = {"metric": metric + ("_adj" if adjust else ""), "start_brt": str(start), "end_brt": str(end),
              "sections_in_window_total": int(((s["DT_BU_RECEBIDO_BRT"] >= start)
                                               & (s["DT_BU_RECEBIDO_BRT"] < end)).sum()),
              "informative_locations": int(loc_id.nunique()), "n_in": int(d["inside"].sum()),
              "n_out": int((~d["inside"]).sum())}
    if result["n_in"] == 0 or result["n_out"] == 0:
        return {**result, "effect": None, "p_value": None, "note": "no location straddles the window"}

    order = np.argsort(loc_id.to_numpy(), kind="stable")
    groups = loc_id.to_numpy()[order]
    x = d[metric].to_numpy()[order]
    lab = d["inside"].to_numpy()[order]

    def stat(l):
        return x[l].mean() - x[~l].mean()

    observed = stat(lab)
    rng = np.random.default_rng(seed)
    null = np.array([stat(_within_group_permutation(groups, lab, rng)) for _ in range(permutations)])
    p = (1 + np.sum(np.abs(null) >= abs(observed))) / (1 + permutations)
    return {**result, "effect": float(observed), "null_sd": float(null.std()),
            "p_value": float(p), "permutations": permutations}
