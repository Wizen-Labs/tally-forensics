"""Geographic filter: residual summaries by state and municipality."""

import numpy as np
import pandas as pd

from .residuals import overdispersion


def summarise(s: pd.DataFrame, by: list[str], min_n: int = 30) -> pd.DataFrame:
    """Per-area residual summary. Under the null, mean residuals sit near 0 and |z| > 3 is rare
    (rarer than 0.27% only if there is no over-dispersion, so compare areas with each other, not with 0.27%)."""
    g = s.groupby(by)
    out = pd.DataFrame({
        "sections": g.size(),
        "share_a": 100 * g["votes_a"].sum() / g["valid"].sum(),
        "share_b": 100 * g["votes_b"].sum() / g["valid"].sum(),
        "mean_margin_resid_pp": 100 * g["margin_resid"].mean(),
        "mean_a_z": g["a_z"].mean(),
        "pct_abs_a_z_gt3": 100 * g["a_z"].apply(lambda z: (z.abs() > 3).mean()),
        "a_z_scale": g["a_z"].apply(overdispersion),
        "mean_turnout_z": g["turnout_z"].mean(),
        "median_lag_min": g["lag_min"].median(),
    })
    return out[out["sections"] >= min_n].sort_values("mean_margin_resid_pp")


def last_digit_test(counts: pd.Series, min_count: int = 100) -> dict:
    """Chi-square of last digits of vote counts against uniform. Weak evidence by design (see METHODOLOGY §4);
    reported for completeness because it is commonly cited, never as a primary test."""
    from scipy.stats import chisquare
    c = counts[counts >= min_count].astype(int)
    if len(c) < 100:
        return {"n": int(len(c)), "chi2": None, "p_value": None}
    observed = np.bincount(c % 10, minlength=10)
    chi2, p = chisquare(observed)
    return {"n": int(len(c)), "chi2": float(chi2), "p_value": float(p), "digits": observed.tolist()}
