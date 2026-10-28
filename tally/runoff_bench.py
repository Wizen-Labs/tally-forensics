"""PHASE 2 (lab). Benchmark of run-off projection models on many real run-offs.

A "case" is one run-off: round-1 sections (base) + round-2 sections (target, with TSE reception times), for one
electoral area (a state for governor run-offs, Brazil for the presidential one). Each case is replayed in real
arrival order; at each checkpoint the model sees only municipal aggregates (what TSE publishes live) and projects
candidate A's share of A+B. Configurations are compared by their errors across cases.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import project

CHECKPOINTS = [0.02, 0.03, 0.05, 0.10, 0.20]


@dataclass(frozen=True)
class Config:
    name: str
    w_transfer: float = 0.5                 # weight of the transfer model in the mean (1 - weight goes to swing)
    k_mun: float = 3000.0                   # swing shrinkage, municipality level (votes)
    k_uf: float = 20000.0                   # swing shrinkage, UF/region level (votes)
    min_frac_corr: float = 0.0              # transfer model: municipal correction only above this completeness
    params: project.Params = field(default_factory=lambda: project.Params(bootstrap=0))


def make_case(r1: pd.DataFrame, r2: pd.DataFrame, nr_a: str, nr_b: str) -> pd.DataFrame:
    df = project.merge_rounds(r1, r2, nr_a, nr_b)
    df = df[df["DT_BU_RECEBIDO_BRT"].notna()].sort_values("DT_BU_RECEBIDO_BRT", kind="stable")
    return df.reset_index(drop=True)


def _aggregates(df: pd.DataFrame, mask: np.ndarray):
    """Municipal aggregates + proportional proxy, exactly as predict_municipal builds them."""
    m = df[df["matched"]].copy()
    cm = mask[df["matched"].to_numpy()]
    mun = ["SG_UF", "CD_MUNICIPIO"]
    m["A2c"], m["B2c"] = np.where(cm, m["A2"], 0), np.where(cm, m["B2"], 0)
    m["apt_c"], m["n_c"] = np.where(cm, m["QT_APTOS"], 0), cm.astype(int)
    agg = m.groupby(mun).agg(**{g: (g, "sum") for g in project.GROUPS}, apt=("QT_APTOS", "sum"),
                             n=("QT_APTOS", "size"), apt_c=("apt_c", "sum"), n_c=("n_c", "sum"),
                             A2c=("A2c", "sum"), B2c=("B2c", "sum")).reset_index()
    agg["frac"] = (agg["apt_c"] / agg["apt"]).where(agg["n_c"] < agg["n"], 1.0).fillna(0)
    Xc = agg[project.GROUPS].to_numpy(float) * agg[["frac"]].to_numpy()
    extra = {t: float(df.loc[~df["matched"] & mask, t].sum()) for t in ("A2", "B2")}
    return agg, Xc, extra


def project_config(df: pd.DataFrame, mask: np.ndarray, cfg: Config) -> float:
    agg, Xc, extra = _aggregates(df, mask)
    tr = project.project_aggregates(agg, Xc, cfg.params, min_frac_corr=cfg.min_frac_corr, extra=extra)["share_a"]
    sw = project.project_swing(agg, Xc, k_mun=cfg.k_mun, k_uf=cfg.k_uf, extra=extra)["share_a"]
    return cfg.w_transfer * tr + (1 - cfg.w_transfer) * sw


def evaluate(cases: dict[str, pd.DataFrame], configs: list[Config], checkpoints=CHECKPOINTS) -> pd.DataFrame:
    """Errors of every config on every case and checkpoint. Each component model is computed once per distinct
    parameter value and the configs are combined afterwards, so a large grid stays cheap."""
    rows = []
    for case, df in cases.items():
        truth = 100 * df["A2"].sum() / (df["A2"].sum() + df["B2"].sum())
        for cp in checkpoints:
            mask = np.arange(len(df)) < int(round(cp * len(df)))
            if mask.sum() == 0:
                continue
            agg, Xc, extra = _aggregates(df, mask)
            tr = {f: project.project_aggregates(agg, Xc, project.Params(bootstrap=0), min_frac_corr=f,
                                                extra=extra)["share_a"]
                  for f in sorted({c.min_frac_corr for c in configs})}
            sw = {(km, ku): project.project_swing(agg, Xc, k_mun=km, k_uf=ku, extra=extra)["share_a"]
                  for km, ku in sorted({(c.k_mun, c.k_uf) for c in configs})}
            for cfg in configs:
                est = cfg.w_transfer * tr[cfg.min_frac_corr] + (1 - cfg.w_transfer) * sw[(cfg.k_mun, cfg.k_uf)]
                rows.append({"case": case, "pct": 100 * cp, "config": cfg.name, "error": est - truth})
    return pd.DataFrame(rows)


def coverage(agg: pd.DataFrame, min_counted: float = 0.01) -> dict:
    """Representativeness of what has been counted, computable live from the progress files.

    - region_min: the smallest share of electorate counted among regions (national case) or among the five
      round-1 lean strata (single-state case, where there is one region);
    - strata_covered: share of the electorate living in (lean decile x size tercile) strata that have at least
      `min_counted` of their electorate counted. Lean = round-1 A/(A+B) of the municipality.
    """
    a = agg.copy()
    a["region"] = a["SG_UF"].map(project.REGION)
    a["counted"] = a["frac"] * a["apt"]
    lean = (a["A1"] / (a["A1"] + a["B1"]).replace(0, np.nan)).fillna(0.5)
    a["lean_bin"] = pd.qcut(lean.rank(method="first"), 10, labels=False)
    a["size_bin"] = pd.qcut(a["apt"].rank(method="first"), 3, labels=False)
    by_region = a.groupby("region")[["counted", "apt"]].sum()
    if len(by_region) == 1:                          # single state: use lean quintiles as "regions"
        by_region = a.groupby(a["lean_bin"] // 2)[["counted", "apt"]].sum()
    st = a.groupby(["lean_bin", "size_bin"])[["counted", "apt"]].sum()
    covered = st["counted"] / st["apt"] >= min_counted
    return {"region_min": float((by_region["counted"] / by_region["apt"]).min()),
            "strata_covered": float(st.loc[covered, "apt"].sum() / st["apt"].sum())}


def evaluate_with_coverage(cases: dict[str, pd.DataFrame], cfg: Config,
                           checkpoints=(0.005, 0.01, 0.015, 0.02, 0.03, 0.05, 0.075, 0.10, 0.15, 0.20)) -> pd.DataFrame:
    """Error of one config together with the coverage metrics, on a fine grid of checkpoints."""
    rows = []
    for case, df in cases.items():
        truth = 100 * df["A2"].sum() / (df["A2"].sum() + df["B2"].sum())
        for cp in checkpoints:
            mask = np.arange(len(df)) < int(round(cp * len(df)))
            if mask.sum() == 0:
                continue
            agg, Xc, extra = _aggregates(df, mask)
            tr = project.project_aggregates(agg, Xc, project.Params(bootstrap=0), min_frac_corr=cfg.min_frac_corr,
                                            extra=extra)["share_a"]
            sw = project.project_swing(agg, Xc, k_mun=cfg.k_mun, k_uf=cfg.k_uf, extra=extra)["share_a"]
            est = cfg.w_transfer * tr + (1 - cfg.w_transfer) * sw
            rows.append({"case": case, "pct": 100 * cp, "error": est - truth, **coverage(agg)})
    return pd.DataFrame(rows)


def summarise(errs: pd.DataFrame) -> pd.DataFrame:
    e = errs.assign(abs_err=errs["error"].abs())
    return (e.groupby("config")["abs_err"]
            .agg(mean="mean", p90=lambda x: x.quantile(0.9), max="max",
                 share_le_05=lambda x: (x <= 0.5).mean())
            .sort_values("p90"))
