"""Live run-off projection from the collector's archive, following the round-2 pre-registration
(PREREGISTRATION_ROUND2.md, config/round2.json).

Estimate = mean of two municipal models with no tuned parameters: the transfer model without prior
(`project_aggregates`) and the municipal swing model (`project_swing`). Interval = estimate +/- a fixed half-width
taken from the envelope of backtest errors. Nothing is published before `min_pct_counted` AND at least
`min_ufs_with_1pct` of the 27 UFs have 1% of their electorate counted (the owner's representativeness rule; abroad is
modelled but is not a UF). A winner is "called" only when the whole interval is on one side of 50%.
"""

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from . import project
from .config import load

MUN = ["SG_UF", "CD_MUNICIPIO"]


def base_by_municipality(r1_sections: pd.DataFrame, nr_a: str, nr_b: str) -> pd.DataFrame:
    x = project.round1_groups(r1_sections, nr_a, nr_b)
    x["CD_MUNICIPIO"] = x["CD_MUNICIPIO"].astype(int).astype(str)
    b = x.groupby(MUN)[project.GROUPS].sum()
    b["n"] = x.groupby(MUN).size()
    return b


def inputs_from_state(state: dict, base: pd.DataFrame, nr_a: str, nr_b: str) -> tuple[pd.DataFrame, np.ndarray, dict]:
    """Municipal table (what TSE has published) joined to the base; Xc by the proportional proxy."""
    ab, mun = state["ab"], state["municipal"]
    for col in ("v_" + nr_a, "v_" + nr_b):
        if col not in mun.columns:
            mun = mun.assign(**{col: 0})
    ucols = [c for c in ("u_sections_counted", "u_sections_total", "u_electorate_counted", "u_electorate_total")
             if c in mun.columns]
    live = ab.merge(mun[MUN + ["v_" + nr_a, "v_" + nr_b] + ucols], on=MUN, how="left").fillna({"v_" + nr_a: 0,
                                                                                                "v_" + nr_b: 0})
    if len(ucols) == 4:
        # Use the progress stated by the municipal file itself, so votes and counts always belong to the same
        # snapshot. A municipality whose file was never read counts as not yet counted (a failed download must
        # not turn into "counted with zero votes").
        has = live["u_sections_counted"].notna()
        live["sections_counted"] = live["u_sections_counted"].where(has, 0)
        live["sections_total"] = live["u_sections_total"].where(has, live["sections_total"])
        live["electorate_counted"] = live["u_electorate_counted"].where(has, 0)
        live["electorate_total"] = live["u_electorate_total"].where(has, live["electorate_total"])
    live["A2c"], live["B2c"] = live["v_" + nr_a], live["v_" + nr_b]
    live["frac"] = np.where(live["sections_counted"] >= live["sections_total"], 1.0,
                            live["electorate_counted"] / live["electorate_total"].clip(lower=1))
    live.loc[live["sections_counted"] == 0, "frac"] = 0.0
    agg = live.join(base, on=MUN, how="inner")
    orphan = live[~live.set_index(MUN).index.isin(base.index)]          # municipalities new since the base
    extra = {"A2": float(orphan["A2c"].sum()), "B2": float(orphan["B2c"].sum())}
    Xc = agg[project.GROUPS].to_numpy(float) * agg[["frac"]].to_numpy()
    return agg, Xc, extra


def project_state(agg: pd.DataFrame, Xc: np.ndarray, extra: dict, cfg: dict) -> dict:
    tr = project.project_aggregates(agg, Xc, project.Params(bootstrap=0), extra=extra)
    sw = project.project_swing(agg, Xc, extra=extra)
    est = (tr["share_a"] + sw["share_a"]) / 2
    h = cfg["half_width_pp"]
    lo, hi = est - h, est + h
    call = "A" if lo > 50 else ("B" if hi < 50 else None)
    return {"estimate_a": est, "lo": lo, "hi": hi, "call": call,
            "transfer_a": tr["share_a"], "swing_a": sw["share_a"]}


def ufs_with_1pct(agg: pd.DataFrame) -> int:
    home = agg[agg["SG_UF"].str.upper() != "ZZ"]
    counted = (home["frac"] * home["electorate_total"]).groupby(home["SG_UF"]).sum()
    total = home["electorate_total"].groupby(home["SG_UF"]).sum().clip(lower=1)
    return int((counted / total >= 0.01).sum())


def project_live(state: dict, base: pd.DataFrame, cfg: dict) -> dict:
    nr_a, nr_b = cfg["candidates"]["A"]["nr"], cfg["candidates"]["B"]["nr"]
    br = state.get("br") or {}
    pct = 100 * br.get("sections_counted", 0) / max(br.get("sections_total", 0), 1)
    raw_a, raw_b = br.get("votes", {}).get(nr_a, 0), br.get("votes", {}).get(nr_b, 0)
    out = {"t_local": datetime.now().isoformat(timespec="seconds"), "br_generated": br.get("generated"),
           "pct_sections_counted": round(pct, 3),
           "raw_a": 100 * raw_a / max(raw_a + raw_b, 1)}
    if pct < cfg["min_pct_counted"]:
        return {**out, "status": f"preliminary: below {cfg['min_pct_counted']}% counted, no projection"}
    agg, Xc, extra = inputs_from_state(state, base, nr_a, nr_b)
    out["ufs_with_1pct"] = ufs_with_1pct(agg)
    if out["ufs_with_1pct"] < cfg.get("min_ufs_with_1pct", 0):
        return {**out, "status": f"preliminary: {out['ufs_with_1pct']} of 27 UFs with 1% counted, "
                                 f"waiting for {cfg['min_ufs_with_1pct']}"}
    return {**out, "status": "projection", **project_state(agg, Xc, extra, cfg)}


def format_line(r: dict, cfg: dict) -> str:
    a, b = cfg["candidates"]["A"]["name"], cfg["candidates"]["B"]["name"]
    head = f"[proj] {r['pct_sections_counted']:6.2f}% counted | raw {a} {r['raw_a']:.2f}%"
    if "ufs_with_1pct" in r:
        head += f" | {r['ufs_with_1pct']} UFs"
    if r["status"] != "projection":
        return f"{head} | {r['status']}"
    call = {"A": f"CALL: {a}", "B": f"CALL: {b}", None: "no call (interval crosses 50%)"}[r["call"]]
    return (f"{head} | projection {a} {r['estimate_a']:.2f}% [{r['lo']:.2f}, {r['hi']:.2f}], "
            f"{b} {100 - r['estimate_a']:.2f}% | {call}")


def load_cfg() -> dict:
    return load("round2_projection")


def make_on_cycle(collector):
    """Callback for Collector.run: project from the archive after every cycle, log and print one line."""
    from . import INTERIM_DIR, live
    full = load_cfg()
    cfg = {**full["projection"], "candidates": full["candidates"]}
    b = full["base"]
    base = base_by_municipality(pd.read_parquet(INTERIM_DIR / f"sections_{b['year']}_t{b['turn']}.parquet"),
                                cfg["candidates"]["A"]["nr"], cfg["candidates"]["B"]["nr"])

    def on_cycle():
        r = project_live(live.load_state(collector.archive), base, cfg)
        append(collector.archive / "projections.jsonl", r)
        print(format_line(r, cfg), flush=True)
    return on_cycle


def append(path: Path, r: dict) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(r, default=str) + "\n")
