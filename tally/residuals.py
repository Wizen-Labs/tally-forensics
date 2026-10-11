"""Section-level residuals against a baseline that needs no model and no other election.

Primary baseline (R1, within-location): sections in the same polling location (same building) serve near-identical
neighbourhoods, so each section is compared with the pooled result of its sibling sections, leaving itself out.
A manipulation that targets sections by transmission time or by box would show up as siblings disagreeing;
a location with genuinely different politics moves all its sections together and cancels out.

What R1 cannot see: a shift applied uniformly to every section of a location (or of the whole country).
"""

import numpy as np
import pandas as pd

LOCATION = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_LOCAL_VOTACAO"]


def within_location(s: pd.DataFrame, num: str, den: str, prefix: str, min_den: int = 30) -> pd.DataFrame:
    """Leave-one-out residual of num/den against sibling sections in the same location.

    Adds <prefix>_resid (proportion points) and <prefix>_z (binomial-scaled).
    """
    s = s.copy()
    ok = s[den] >= min_den
    g = s[ok].groupby(LOCATION)
    tot_num = g[num].transform("sum")
    tot_den = g[den].transform("sum")
    n_sib = g[num].transform("size") - 1

    sib_num = tot_num - s.loc[ok, num]
    sib_den = tot_den - s.loc[ok, den]
    p_i = s.loc[ok, num] / s.loc[ok, den]
    p_sib = sib_num / sib_den.replace(0, np.nan)
    var = p_sib * (1 - p_sib) * (1 / s.loc[ok, den] + 1 / sib_den.replace(0, np.nan))

    resid = (p_i - p_sib).where(n_sib >= 1)
    z = (resid / np.sqrt(var)).replace([np.inf, -np.inf], np.nan)

    s[f"{prefix}_resid"] = np.nan
    s[f"{prefix}_z"] = np.nan
    s[f"{prefix}_siblings"] = np.nan
    s.loc[ok, f"{prefix}_resid"] = resid
    s.loc[ok, f"{prefix}_z"] = z
    s.loc[ok, f"{prefix}_siblings"] = n_sib
    return s


def add_all(s: pd.DataFrame, min_valid: int) -> pd.DataFrame:
    s = within_location(s, "votes_a", "valid", "a", min_valid)
    s = within_location(s, "votes_b", "valid", "b", min_valid)
    s = within_location(s, "QT_COMPARECIMENTO", "QT_APTOS", "turnout", min_valid)
    s["margin_resid"] = s["a_resid"] - s["b_resid"]
    return s


CLOSE_DELAY_EDGES = [-np.inf, 5, 15, 30, 60, 120, np.inf]


def add_covariates(s: pd.DataFrame, election_day: pd.Timestamp) -> pd.DataFrame:
    """Pre-transmission covariates, fixed at the polling station before any data leaves the box.

    Calibration on 2022 (FINDINGS.md) showed they explain the placebo-window signal:
    - close delay: queues keep some sections open past 17:00; those voters differ and their BUs arrive later;
    - section rank within the location: newer sections hold newer (younger) registrations.
    """
    s = s.copy()
    close = election_day + pd.Timedelta(hours=17)
    s["close_delay_min"] = (s["DT_ENCERRAMENTO_BRT"] - close).dt.total_seconds() / 60
    s["close_bucket"] = pd.cut(s["close_delay_min"], CLOSE_DELAY_EDGES, labels=False)
    s["_sec"] = pd.to_numeric(s["NR_SECAO"])
    rank = s.groupby(LOCATION)["_sec"].rank(pct=True)
    s = s.drop(columns="_sec")
    s["sec_rank_q"] = np.ceil(rank * 5).clip(1, 5)
    s["log_aptos"] = np.log(s["QT_APTOS"].clip(lower=1))
    return s


def design_matrix(d: pd.DataFrame) -> np.ndarray:
    """Dummies for close-delay bucket and section-rank quintile, plus log size and the aggregated flag."""
    parts = [pd.get_dummies(d["close_bucket"].astype(int), prefix="cb", drop_first=True, dtype=float),
             pd.get_dummies(d["sec_rank_q"].astype(int), prefix="rq", drop_first=True, dtype=float),
             d[["log_aptos"]].astype(float), d[["aggregated"]].astype(float)]
    return pd.concat(parts, axis=1).to_numpy()


def overdispersion(z: pd.Series) -> float:
    """Robust scale of z (1.0 = pure binomial noise). Reported, not used to tune tests."""
    z = z.dropna()
    return float(1.4826 * np.median(np.abs(z - np.median(z)))) if len(z) else float("nan")
