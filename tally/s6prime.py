"""S6' (deviation 01 of H8r2): synchrony across boxes at real vote rates.

The frozen S6 needs 6-10 votes in one box-minute, which a real box never casts (at most 3), so it cannot fire. S6'
keeps the question (one trigger, many boxes, the same clock minute) and uses rates that occur:
  - A: box-minutes with at least 3 votes ("peaks"); the count of boxes peaking in each BRT minute against a local
    baseline (Poisson, add-one);
  - B1, B2: total votes of all boxes in each 1-minute and 2-minute bin against a local baseline, with the
    overdispersion estimated from all bins (robust). B sees a trigger of one vote per box in many boxes.
The expected count of a bin is its exposure (boxes in their interior) times the rate of the bins within +-20
minutes, leaving out the bin and its close neighbours, in a window kept symmetric near the ends of the day (a linear
trend cancels). The time-of-day profile (opening queue, lunch, closing) and the number of open boxes are kept. Bins
with fewer than 5 baseline minutes on a side are not tested. Only each box's interior is used: from 15 minutes
after its first vote to 15 minutes before its last.
Spec and decision rule: commitments/deviation_01_s6prime.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.01
EDGE_MIN = 15
WINDOW_MIN = 20
PEAK = 3
MIN_SIDE = 5


def minutes(v: pd.DataFrame, offset_h: pd.Series) -> tuple[pd.DataFrame, pd.Series]:
    """BRT minute of each vote, kept only in each box's interior (boxes with a known offset), and the exposure:
    the number of boxes in their interior at each minute."""
    off = v["box"].map(offset_h)
    d = v.loc[off.notna(), ["box"]].copy()
    d["minute"] = ((v.loc[off.notna(), "t_computed"] + off[off.notna()] * 3600) // 60).astype(np.int64)
    g = d.groupby("box")["minute"]
    lo, hi = g.min() + EDGE_MIN, g.max() - EDGE_MIN
    keep = hi >= lo
    lo, hi = lo[keep], hi[keep]
    m0, m1 = int(lo.min()), int(hi.max())
    diff = np.zeros(m1 - m0 + 2)
    np.add.at(diff, (lo - m0).to_numpy(), 1)
    np.add.at(diff, (hi - m0 + 1).to_numpy(), -1)
    exposure = pd.Series(np.cumsum(diff)[:-1], index=np.arange(m0, m1 + 1))
    d = d[d["box"].isin(lo.index)]
    d = d[(d["minute"] >= d["box"].map(lo)) & (d["minute"] <= d["box"].map(hi))]
    return d, exposure


def _window(x: np.ndarray, half: int, gap: int) -> tuple[np.ndarray, np.ndarray]:
    """Sum of x over offsets gap+1..h on both sides, with h = min(half, distance to either end), so the window is
    always symmetric and a linear trend cancels; and the number of bins on each side."""
    n = len(x)
    c = np.concatenate([[0.0], np.cumsum(x)])
    idx = np.arange(n)
    h = np.minimum(half, np.minimum(idx, n - 1 - idx))
    side = np.clip(h - gap, 0, None)
    lo, hi = np.clip(idx - gap, 0, n), np.clip(idx + gap + 1, 0, n)
    s = (c[lo] - c[np.clip(lo - side, 0, n)]) + (c[np.clip(hi + side, 0, n)] - c[hi])
    return s, side


def _bins(d: pd.DataFrame, exposure: pd.Series, width: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    grid = np.arange(exposure.index.min() // width, exposure.index.max() // width + 1)
    e = exposure.groupby(exposure.index // width).sum().reindex(grid, fill_value=0).to_numpy(float)
    v = (d["minute"] // width).value_counts().reindex(grid, fill_value=0).to_numpy(float)
    return grid, v, e


def stat_a(d: pd.DataFrame, exposure: pd.Series) -> pd.DataFrame:
    """A: boxes peaking (>= PEAK votes) per minute; expected = exposure x the window's peaks per box-minute
    (add-one), Poisson."""
    cnt = d.groupby(["box", "minute"]).size()
    peaks = cnt[cnt >= PEAK].reset_index()
    grid, _, e = _bins(d, exposure, 1)
    p_m = peaks.groupby("minute")["box"].nunique().reindex(grid, fill_value=0).to_numpy(float)
    sp, side = _window(p_m, WINDOW_MIN, 2)
    se, _ = _window(e, WINDOW_MIN, 2)
    ok = (side >= MIN_SIDE) & (se > 0) & (e > 0)
    lam = np.where(ok, e * (sp + 1) / np.where(se > 0, se, 1), 1.0)
    p = np.where(ok, stats.poisson.sf(p_m - 1, lam), 1.0)
    out = pd.DataFrame({"minute": grid, "count": p_m, "expected": lam, "exposure": e, "p": p, "tested": ok})
    out["flag"] = out["p"] < ALPHA / max(int(ok.sum()), 1)
    return out


def stat_b(d: pd.DataFrame, exposure: pd.Series, width: int) -> pd.DataFrame:
    """B: total votes per bin of `width` minutes; expected = exposure x the window's votes per box-minute;
    overdispersion from all tested bins (robust)."""
    grid, v, e = _bins(d, exposure, width)
    half, gap = WINDOW_MIN // width, max(2 // width, 1)
    sv, side = _window(v, half, gap)
    se, _ = _window(e, half, gap)
    ok = (side >= MIN_SIDE // width) & (se > 0) & (e > 0)
    base = np.where(ok, e * sv / np.where(se > 0, se, 1), 0.0)
    ok &= base > 0
    r = np.where(ok, (v - base) / np.sqrt(np.where(ok, base, 1)), 0.0)
    phi = max(np.median(r[ok] ** 2) / stats.chi2.median(1), 1.0)
    z = r / np.sqrt(phi)
    p = np.where(ok, stats.norm.sf(z), 1.0)
    out = pd.DataFrame({"minute": grid * width, "count": v, "expected": base, "exposure": e, "z": z, "p": p,
                        "phi": phi, "tested": ok})
    out["flag"] = out["p"] < ALPHA / max(int(ok.sum()), 1)
    return out


def run(v: pd.DataFrame, offset_h: pd.Series) -> dict[str, pd.DataFrame]:
    d, e = minutes(v, offset_h)
    return {"A": stat_a(d, e), "B1": stat_b(d, e, 1), "B2": stat_b(d, e, 2)}


def coincide(flags_d: list[int], flags_c: list[int], flags_ctrl: list[int], tol: int = 2) -> list[int]:
    """Round-2 minutes flagged in both halves (within tol) and with no round-1 flag at the same time of day."""
    out = []
    for m in flags_d:
        tod = m % 1440
        if any(abs(m - x) <= tol for x in flags_c) and not any(abs(tod - x % 1440) <= tol for x in flags_ctrl):
            out.append(m)
    return out
