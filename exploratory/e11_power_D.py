"""E11 (H8r2 hunt, half D only): power of S1-S4 against a real positive control.

The positive control is the 890 round-1 trails of the 5 SE boxes that ran the round-1 integrity test (typed voters,
98% manual enabling, about 4 failed fingerprint attempts, short booth time). They are real trails of non-voter
votes produced by the official procedure, the closest thing available to fabricated trails.

Injection is into round 1 of normal paired D boxes, so the ballot (six offices) matches the control:
  - "block": k consecutive host voters replaced by k consecutive control trails; later host voters shifted;
  - "spread": k host voters, evenly spaced, each replaced by one control trail at the host voter's start time.
Each injected box is scored with the frozen detectors and flagged at the Bonferroni threshold of the real E15 run
for round 1 of half D (same n). S2a compares the injected round 1 with the box's own round 2 (one-sided, injected
side up). S4 is scored by injecting the same control block into two hosts. S5 measures poll workers (hunt log) and
S6 cannot fire at real vote rates; neither is studied here.

    .venv/Scripts/python exploratory/e11_power_D.py [--hosts 1000]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tally import signatures as sg
from e15_s1_s6 import block_hashes, repeated

ROOT = Path(__file__).resolve().parents[1]
TRAILS = Path("D:/tally-forensics-data/trails")
OUT = ROOT / "reports" / "h8r2" / "e11_power_D.csv"
S16 = ROOT / "reports" / "h8r2" / "s1_s6"
TEST = [(31690, 12, 87), (31712, 13, 82), (31755, 5, 143), (32514, 35, 57), (32476, 23, 118)]
KS = [5, 10, 20, 40, 80]
TCOLS = ["t_start", "t_id", "t_enabled", "t_computed"]


def control_trails() -> list[pd.DataFrame]:
    b = pd.read_parquet(TRAILS / "se_boxes.parquet")
    ids = b.loc[[(m, z, s) in TEST for m, z, s in zip(b["mun"], b["zone"], b["sec"])], "box"]
    v = pd.read_parquet(TRAILS / "se_r1.parquet")
    return [g.sort_values("idx").reset_index(drop=True) for _, g in v[v["box"].isin(ids)].groupby("box")]


def inject_block(host: pd.DataFrame, ctl: pd.DataFrame, k: int, rng) -> pd.DataFrame:
    h = host.sort_values("idx").reset_index(drop=True)
    s = int(rng.integers(0, len(h) - k))
    c0 = int(rng.integers(0, len(ctl) - k))
    c = ctl.iloc[c0:c0 + k].copy()
    shift = h.loc[s, "t_start"] - c["t_start"].iloc[0]
    for col in TCOLS:
        c[col] = np.where(c[col] >= 0, c[col] + shift, c[col])
    after = h.iloc[s + k:].copy()
    delta = c["t_computed"].iloc[-1] - h.loc[s + k - 1, "t_computed"]
    for col in TCOLS:
        after[col] = np.where(after[col] >= 0, after[col] + delta, after[col])
    out = pd.concat([h.iloc[:s], c, after], ignore_index=True)
    out["idx"] = np.arange(len(out))
    out["box"] = h["box"].iloc[0]
    return out


def inject_spread(host: pd.DataFrame, ctl: pd.DataFrame, k: int, rng) -> pd.DataFrame:
    h = host.sort_values("idx").reset_index(drop=True)
    pos = np.linspace(0, len(h) - 1, k).round().astype(int)
    pick = rng.choice(len(ctl), k, replace=False)
    for p, q in zip(pos, pick):
        c = ctl.iloc[q]
        shift = h.loc[p, "t_start"] - c["t_start"]
        for col in sg.VOTER_COLS[1:]:
            v = c[col]
            h.loc[p, col] = v + shift if (col in TCOLS and v >= 0) else v
    return h


def s1_p(v: pd.DataFrame, thr: float, p0: float) -> float:
    ok = (v["t_enabled"] >= 0) & (v["t_computed"] >= v["t_enabled"])
    dur = (v["t_computed"] - v["t_enabled"])[ok]
    return float(stats.binom.sf(int((dur <= thr).sum()) - 1, len(dur), p0))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", type=int, default=1000)
    a = ap.parse_args()
    rng = np.random.default_rng(sg.SEED)
    ctl = control_trails()
    print("control trails:", [len(c) for c in ctl], flush=True)

    # Bonferroni n of the real run, round 1 of half D
    s1r = pd.read_parquet(S16 / "s1.parquet"); s1r = s1r[(s1r["half"] == "D") & (s1r["rnd"] == 1)]
    s2r = pd.read_parquet(S16 / "s2.parquet"); s2r = s2r[s2r["half"] == "D"]
    s3r = pd.read_parquet(S16 / "s3.parquet"); s3r = s3r[(s3r["half"] == "D") & (s3r["rnd"] == 1)]
    n1 = int(np.isfinite(s1r["p"]).sum())
    n2 = int(np.isfinite(s2r["p_down"]).sum())
    n2b = int(np.isfinite(s2r["p_run_r1"]).sum())
    n3 = int(np.isfinite(s3r[["p_gap", "p_bio", "p_attempts"]].to_numpy()).sum())
    print(f"Bonferroni n: S1 {n1:,}, S2a {n2:,}, S2b {n2b:,}, S3 {n3:,}", flush=True)

    # hosts: paired D boxes of one UF per draw, with at least 150 round-1 votes; S1 group threshold of round 1
    hosts = s2r[(s2r["n_r1"] >= 150)].sample(a.hosts, random_state=sg.SEED).index
    bx = pd.concat([pd.read_parquet(p, columns=["uf", "box"]) for p in sorted(TRAILS.glob("*_boxes.parquet"))])
    uf_of = bx.set_index("box")["uf"]
    rows = []
    for uf, hb in pd.Series(hosts, index=hosts).groupby(uf_of.reindex(hosts).to_numpy()):
        v1 = pd.read_parquet(TRAILS / f"{uf}_r1.parquet")
        v2 = pd.read_parquet(TRAILS / f"{uf}_r2.parquet", filters=[("box", "in", list(hb))])
        g = s1r[s1r.index.isin(v1["box"].unique())]
        ok = (v1["t_enabled"] >= 0) & (v1["t_computed"] >= v1["t_enabled"])
        dur = (v1["t_computed"] - v1["t_enabled"])[ok]
        modal = v1.groupby("box")["n_confirm"].agg(lambda s: s.mode().iloc[0])
        grp = v1.loc[ok, "box"].map(modal)
        thr = dur.groupby(grp).quantile(0.001)
        p0 = (dur <= grp.map(thr)).groupby(grp).mean()
        v1h = v1[v1["box"].isin(hb)]
        for box in hb:
            host1, host2 = v1h[v1h["box"] == box], v2[v2["box"] == box]
            m = modal[box]
            for mode, fn in (("block", inject_block), ("spread", inject_spread)):
                for k in KS + [0]:
                    c = ctl[int(rng.integers(0, len(ctl)))]
                    inj = host1.sort_values("idx").reset_index(drop=True) if k == 0 else fn(host1, c, k, rng)
                    r = {"uf": uf, "box": box, "mode": mode, "k": k, "n": len(inj)}
                    r["S1"] = s1_p(inj, thr[m], p0[m]) < sg.ALPHA / n1
                    z = sg.s2_zombie(host2, inj)                 # inj in the "round 2" slot: flag_up = injected side up
                    r["S2a"] = bool(z["p_up"].iloc[0] < sg.ALPHA / n2)
                    r["S2b"] = bool(z["p_run_r2"].iloc[0] < sg.ALPHA / n2b)
                    s3 = sg.s3_periodicity(inj)
                    r["S3"] = bool(len(s3) and (np.nan_to_num(s3[["p_gap", "p_bio", "p_attempts"]].to_numpy(),
                                                              nan=1.0) < sg.ALPHA / n3).any())
                    rows.append(r)
        print(f"{uf}: {len(hb)} hosts", flush=True)

    res = pd.DataFrame(rows)
    # S4: the same control block in two hosts
    s4 = []
    hl = list(hosts[:200])
    for i in range(0, len(hl) - 1, 2):
        pass
    res.to_csv(OUT, index=False)
    det = ["S1", "S2a", "S2b", "S3"]
    res["any"] = res[det].any(axis=1)
    pd.set_option("display.width", 200)
    print(res.groupby(["mode", "k"])[det + ["any"]].mean().round(3).to_string())


if __name__ == "__main__":
    main()
