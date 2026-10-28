"""E15 (H8r2 §3): fixed log detectors S1-S6 on both halves, round 2 against the round-1 control.

Inputs: the E12 trail tables (`<uf>_r1/_r2/_boxes.parquet`), round-1 bweb sections (aggregation flag, turnout,
time-zone offset) and the E8 replaced/unexplained cases. Outputs in `reports/h8r2/s1_s6/`:
  - `s1.parquet`, `s2.parquet`, `s3.parquet`, `s5.parquet`: per-box statistics, both rounds where defined;
  - `s4_blocks.csv`: repeated 10-voter blocks (box lists) per half and round;
  - `s6.json`, `decision.csv`: synchrony results and the §3 decision table per half;
  - `flagged.csv`: every flagged box with its section, detector and round;
  - `exclusions.csv`: every excluded log with its reason.

Memory: the trail tables do not fit in RAM, so the per-box detectors run on chunks of boxes and Bonferroni flags
are recomputed over the whole half with the frozen `bonferroni_flags`. Two detectors cannot be chunked as written:
  - S4 compares blocks across boxes. `block_hashes` repeats the frozen hashing of `s4_repetition` line by line and
    returns every within-box block hash; repeated blocks are then found over the half;
  - S5 bins scores on the deciles of the national round-1 scores (§3). The frozen function takes the deciles of
    whatever round-1 table it gets; `s5_with_edges` is the same code with the national edges passed in.
`--check` verifies both against the frozen functions on one whole UF before anything else runs.

Exclusions (§1):
  - all detectors: sections with aggregated sections (round-1 bweb; the round-2 file is not yet out);
  - round-1 tables (the control): the 5 SE sections whose round-1 log is a round-1 integrity test (hunt log);
  - paired detectors (S2, S5): a log is paired only if it is the section's only log, its round-1 vote count equals
    the round-1 bweb turnout of the section (same box for the whole round-1 day), and E8 did not mark the section
    replaced or unexplained.
Known device cases are not excluded; they are marked in `flagged.csv`.

    .venv/Scripts/python exploratory/e15_s1_s6.py [--check ac] [--procs 6]
"""
import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tally import INTERIM_DIR
from tally import signatures as sg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "h8r2" / "s1_s6"
TRAILS = Path("D:/tally-forensics-data/trails")
CHUNK = 1_500_000                                   # round-2 trails per chunk
SE_TEST = [("se", 31690, 12, 87), ("se", 31712, 13, 82), ("se", 31755, 5, 143), ("se", 32514, 35, 57),
           ("se", 32476, 23, 118)]
KNOWN = {("rj", 60011, 8, 74): "C-01 device (contingency UE2013, manual share)",
         ("ba", 38830, 162, 153): "round-1 reader pattern (open, low priority)",
         ("rs", 88188, 81, 293): "round-1 reader pattern (open, low priority)"}
SEC = ["uf", "mun", "zone", "sec"]


# ---------------------------------------------------------------- chunkable forms of S4 and S5

def block_hashes(v: pd.DataFrame, block: int = 10) -> pd.DataFrame:
    """Every within-box block hash of `s4_repetition` (same code up to the cross-box step)."""
    cols = ["id_type", "photo", "attempts", "n_scores", "bio", "n_confirm", "bad_keys"]
    s = v.sort_values(["box", "idx"], kind="stable")
    tok = np.column_stack([s[c].to_numpy() for c in cols] + [
        (s["t_id"] - s["t_start"]).to_numpy(), (s["t_enabled"] - s["t_id"]).to_numpy(),
        (s["t_computed"] - s["t_enabled"]).to_numpy()]).astype(np.int64)
    with np.errstate(over="ignore"):
        h = np.zeros(len(s), dtype=np.uint64)
        for j in range(tok.shape[1]):
            h = (h ^ (tok[:, j].astype(np.uint64) + np.uint64(0x9E3779B97F4A7C15) + (h << np.uint64(6))
                      + (h >> np.uint64(2)))) * np.uint64(0xBF58476D1CE4E5B9)
        n = len(s) - block + 1
        if n <= 0:
            return pd.DataFrame({"hash": np.array([], np.uint64), "box": np.array([], np.int64)})
        H = np.zeros(n, dtype=np.uint64)
        for k in range(block):
            H = H * np.uint64(1099511628211) + h[k:k + n]
    box = s["box"].to_numpy()
    same = box[:n] == box[block - 1:block - 1 + n]
    return pd.DataFrame({"hash": H[same], "box": box[:n][same]}).drop_duplicates()


def repeated(h: pd.DataFrame) -> pd.DataFrame:
    """The cross-box step of `s4_repetition`."""
    cnt = h.groupby("hash")["box"].nunique()
    rep = h[h["hash"].isin(cnt[cnt >= 2].index)]
    out = rep.groupby("hash")["box"].agg(n_boxes="nunique", boxes=lambda x: sorted(x.tolist())).reset_index()
    out["hash"] = out["hash"].map(lambda x: f"{int(x):016x}")
    return out


def s5_with_edges(v1: pd.DataFrame, v2: pd.DataFrame, edges: np.ndarray, min_n: int = 20) -> pd.DataFrame:
    """`s5_scores` with the decile edges given (national round 1) instead of taken from `v1`."""
    s1, s2 = v1[v1["n_scores"] > 0], v2[v2["n_scores"] > 0]

    def chi(a, b):
        ca, _ = np.histogram(a, edges)
        cb, _ = np.histogram(b, edges)
        keep = (ca + cb) > 0
        if keep.sum() < 2:
            return np.nan
        return stats.chi2_contingency(np.vstack([ca[keep], cb[keep]]))[1]

    g1, g2 = dict(tuple(s1.groupby("box")["score_last"])), dict(tuple(s2.groupby("box")["score_last"]))
    rows = []
    for box in g1.keys() & g2.keys():
        a, b = g1[box].to_numpy(), g2[box].to_numpy()
        if len(a) >= min_n and len(b) >= min_n:
            rows.append({"box": box, "p": chi(b, a), "p_ctrl": chi(a[0::2], a[1::2])})
    return pd.DataFrame(rows, columns=["box", "p", "p_ctrl"]).set_index("box")


def national_edges() -> np.ndarray:
    s = np.concatenate([pd.read_parquet(p, columns=["n_scores", "score_last"]).query("n_scores > 0")["score_last"]
                        .to_numpy() for p in sorted(TRAILS.glob("*_r1.parquet"))])
    edges = np.unique(np.quantile(s, np.linspace(0, 1, 11)))
    edges[0], edges[-1] = -np.inf, np.inf
    return edges


# ---------------------------------------------------------------- box selection

def box_table() -> tuple[pd.DataFrame, pd.DataFrame]:
    b = pd.concat([pd.read_parquet(p) for p in sorted(TRAILS.glob("*_boxes.parquet"))], ignore_index=True)
    b["half"] = b["uf"].str.upper().map(sg.split_ufs(sorted(b["uf"].unique())))
    bw = pd.read_parquet(INTERIM_DIR / "sections_2026_t1.parquet",
                         columns=["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO", "QT_COMPARECIMENTO", "aggregated",
                                  "tz_offset_h"])
    bw = bw.assign(uf=bw["SG_UF"].str.lower(), mun=bw["CD_MUNICIPIO"].astype(int), zone=bw["NR_ZONA"].astype(int),
                   sec=bw["NR_SECAO"].astype(int))[SEC + ["QT_COMPARECIMENTO", "aggregated", "tz_offset_h"]]
    off = bw.groupby(["uf", "mun"], as_index=False)["tz_offset_h"].first()
    b = b.merge(bw.drop(columns="tz_offset_h"), on=SEC, how="left").merge(off, on=["uf", "mun"], how="left")
    e8 = pd.read_csv(ROOT / "reports" / "e8_urna_logs" / "round1_validation_cases.csv")
    e8 = set(zip(e8["SG_UF"].str.lower(), e8["mun"], e8["zone"], e8["sec"]))
    key = list(zip(b["uf"], b["mun"], b["zone"], b["sec"]))
    n_logs = b.groupby(SEC)["box"].transform("size")
    b["excl_all"] = b["aggregated"].fillna(False).astype(bool)
    b["excl_r1"] = b["excl_all"] | pd.Series([k in SE_TEST for k in key], index=b.index)
    b["paired"] = (~b["excl_r1"] & (n_logs == 1) & (b["votes_r1"] == b["QT_COMPARECIMENTO"])
                   & pd.Series([k not in e8 for k in key], index=b.index))
    b["known"] = [KNOWN.get(k, "") for k in key]
    ex = pd.concat([b[b["excl_all"]].assign(reason="aggregated (round-1 bweb)"),
                    b[b["excl_r1"] & ~b["excl_all"]].assign(reason="round-1 integrity test (round 1 only)"),
                    b[~b["paired"] & ~b["excl_r1"]].assign(reason="not paired (S2, S5 only)")])
    return b, ex[SEC + ["sha12", "box", "half", "votes_r1", "QT_COMPARECIMENTO", "reason"]]


def chunks(b: pd.DataFrame) -> list[tuple[str, int, int]]:
    out = []
    for uf, g in b.groupby("uf"):
        g = g.sort_values("box")
        part = (g["votes_r2"].cumsum() // CHUNK).to_numpy()
        for k in np.unique(part):
            ids = g["box"].to_numpy()[part == k]
            out.append((uf, int(ids.min()), int(ids.max())))
    return out


# ---------------------------------------------------------------- workers

def read(uf: str, rnd: int, lo: int, hi: int, cols=None) -> pd.DataFrame:
    return pd.read_parquet(TRAILS / f"{uf}_r{rnd}.parquet", columns=cols,
                           filters=[("box", ">=", lo), ("box", "<=", hi)])


def chunk_task(args) -> dict:
    uf, lo, hi, keep1, keep2, paired, edges = args
    v1 = read(uf, 1, lo, hi)
    v2 = read(uf, 2, lo, hi)
    v1 = v1[v1["box"].isin(keep1)]
    v2 = v2[v2["box"].isin(keep2)]
    p1, p2 = v1[v1["box"].isin(paired)], v2[v2["box"].isin(paired)]
    s3 = pd.concat([sg.s3_periodicity(v).drop(columns="flag", errors="ignore").assign(rnd=r)
                    for r, v in ((1, v1), (2, v2))])
    return {"s2": sg.s2_zombie(p1, p2) if len(p1) and len(p2) else pd.DataFrame(),
            "s3": s3,
            "s5": s5_with_edges(p1, p2, edges),
            "h1": block_hashes(v1), "h2": block_hashes(v2)}


def s1_task(args) -> pd.DataFrame:
    uf, keep1, keep2 = args
    out = []
    for rnd, keep in ((1, keep1), (2, keep2)):
        v = pd.read_parquet(TRAILS / f"{uf}_r{rnd}.parquet", columns=["box", "t_enabled", "t_computed", "n_confirm"])
        v = v[v["box"].isin(keep)]
        modal = v.groupby("box")["n_confirm"].agg(lambda s: s.mode().iloc[0])   # same as sg.ballot_group
        labels = {k: f"{uf.upper()}:{k}" for k in modal.unique()}          # shared string objects: low memory
        v["group"] = v["box"].map(modal).map(labels).astype(object)
        r = sg.s1_turbo(v).drop(columns="flag")
        out.append(r.assign(rnd=rnd, group=r["group"].astype(str)))
    return pd.concat(out)


# ---------------------------------------------------------------- check against the frozen functions

def check(uf: str) -> None:
    v1 = pd.read_parquet(TRAILS / f"{uf}_r1.parquet")
    v2 = pd.read_parquet(TRAILS / f"{uf}_r2.parquet")
    inj = v2.copy()                                  # positive case: one 10-voter block copied into another box
    boxes = inj["box"].unique()
    src = inj[(inj["box"] == boxes[0]) & inj["idx"].between(20, 29)]
    tgt = inj.index[(inj["box"] == boxes[1]) & inj["idx"].between(50, 59)]
    shift = inj.loc[tgt[0], "t_start"] - src["t_start"].iloc[0]
    for c in sg.VOTER_COLS[1:]:
        inj.loc[tgt, c] = src[c].to_numpy() + (shift if c.startswith("t_") else 0)
    assert len(sg.s4_repetition(inj)) >= 1
    for v in (v1, v2, inj):
        a = sg.s4_repetition(v).sort_values("hash").reset_index(drop=True)
        b = repeated(block_hashes(v)).sort_values("hash").reset_index(drop=True)
        assert a.equals(b), "S4 chunked form differs from the frozen function"
    s1 = v1[v1["n_scores"] > 0]
    edges = np.unique(np.quantile(s1["score_last"], np.linspace(0, 1, 11)))
    edges[0], edges[-1] = -np.inf, np.inf
    a = sg.s5_scores(v1, v2)[["p", "p_ctrl"]].sort_index()
    b = s5_with_edges(v1, v2, edges).sort_index()
    assert np.allclose(a.to_numpy(), b.to_numpy(), equal_nan=True) and (a.index == b.index).all(), "S5 differs"
    print(f"check {uf}: S4 ({len(sg.s4_repetition(v2))} repeated blocks in round 2) and S5 "
          f"({len(a)} boxes) identical to the frozen functions", flush=True)


# ---------------------------------------------------------------- half-level steps

def s3_flags(s3: pd.DataFrame) -> pd.DataFrame:
    p = s3[["p_gap", "p_bio", "p_attempts"]].to_numpy()
    n = np.isfinite(p).sum()
    s3["flag"] = (np.nan_to_num(p, nan=1.0) < sg.ALPHA / max(n, 1)).any(axis=1)
    return s3


def s6_half(b: pd.DataFrame, half: str, rnd: int, keep: set) -> dict:
    parts = []
    for uf in sorted(b.loc[b["half"] == half, "uf"].unique()):
        v = pd.read_parquet(TRAILS / f"{uf}_r{rnd}.parquet", columns=["box", "t_computed"])
        parts.append(v[v["box"].isin(keep)])
    v = pd.concat(parts, ignore_index=True)
    off = b.set_index("box")["tz_offset_h"]
    off = off[off.notna()]
    v = v[v["box"].isin(off.index)]
    return sg.s6_synchrony(v, off)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", default="ac")
    ap.add_argument("--procs", type=int, default=6)
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    check(a.check)
    b, ex = box_table()
    ex.to_csv(OUT / "exclusions.csv", index=False)
    keep1 = set(b.loc[~b["excl_r1"], "box"])
    keep2 = set(b.loc[~b["excl_all"], "box"])
    paired = set(b.loc[b["paired"], "box"])
    print(f"{len(b):,} logs; round 2 kept {len(keep2):,}, round 1 kept {len(keep1):,}, paired {len(paired):,}",
          flush=True)
    edges = national_edges()
    print("national round-1 score deciles:", edges[1:-1].tolist(), flush=True)

    jobs = chunks(b)
    res = {"s2": [], "s3": [], "s5": [], "h1": [], "h2": []}
    with ProcessPoolExecutor(a.procs) as ex_:
        s1 = pd.concat(ex_.map(s1_task, [(uf, keep1, keep2) for uf in sorted(b["uf"].unique())]))
        print("S1 done", flush=True)
        args = [(uf, lo, hi, keep1 & set(range(lo, hi + 1)), keep2 & set(range(lo, hi + 1)),
                 paired & set(range(lo, hi + 1)), edges) for uf, lo, hi in jobs]
        for i, r in enumerate(ex_.map(chunk_task, args), 1):
            for k in res:
                res[k].append(r[k])
            if i % 10 == 0:
                print(f"chunks {i}/{len(jobs)}", flush=True)

    half = b.set_index("box")["half"]
    s1["half"] = s1.index.map(half)
    s2 = pd.concat(res["s2"]); s2["half"] = s2.index.map(half)
    s3 = pd.concat(res["s3"]); s3["half"] = s3.index.map(half)
    s5 = pd.concat(res["s5"]); s5["half"] = s5.index.map(half)
    s1["flag"], s3["flag"], s5["flag"], s5["flag_ctrl"] = False, False, False, False
    h = {r: pd.concat(res[f"h{r}"], ignore_index=True) for r in (1, 2)}

    rows, flagged, s4_out, s6_out = [], [], [], {}
    for hf in ("D", "C"):
        for r in (1, 2):
            m = (s1["half"] == hf) & (s1["rnd"] == r)
            s1.loc[m, "flag"] = sg.bonferroni_flags(s1.loc[m, "p"].to_numpy())
            m3 = (s3["half"] == hf) & (s3["rnd"] == r)
            s3.loc[m3, "flag"] = s3_flags(s3[m3].copy())["flag"].to_numpy()
        m2, m5 = s2["half"] == hf, s5["half"] == hf
        for df, m, cols in ((s2, m2, {"p_up": "flag_up", "p_down": "flag_down", "p_run_r1": "flag_run_r1",
                                      "p_run_r2": "flag_run_r2"}), (s5, m5, {"p": "flag", "p_ctrl": "flag_ctrl"})):
            for pc, fc in cols.items():
                df.loc[m, fc] = sg.bonferroni_flags(df.loc[m, pc].to_numpy())
        reps = {}
        for r in (1, 2):
            hh = h[r][h[r]["box"].map(half) == hf]
            reps[r] = repeated(hh)
            s4_out.append(reps[r].assign(half=hf, rnd=r))
        s4n = {r: len(set(x for L in reps[r]["boxes"] for x in L)) for r in (1, 2)}
        s6 = {r: s6_half(b, hf, r, keep1 if r == 1 else keep2) for r in (1, 2)}
        s6_out[hf] = s6
        print(f"{hf}: S4 and S6 done", flush=True)
        c = lambda df, m, col: int(df.loc[m, col].fillna(False).astype(bool).sum())
        for det, f2, f1 in (
                ("S1", c(s1, (s1["half"] == hf) & (s1["rnd"] == 2), "flag"),
                 c(s1, (s1["half"] == hf) & (s1["rnd"] == 1), "flag")),
                ("S2a", c(s2, m2, "flag_up"), c(s2, m2, "flag_down")),
                ("S2b", c(s2, m2, "flag_run_r2"), c(s2, m2, "flag_run_r1")),
                ("S3", c(s3, (s3["half"] == hf) & (s3["rnd"] == 2), "flag"),
                 c(s3, (s3["half"] == hf) & (s3["rnd"] == 1), "flag")),
                ("S4", s4n[2], s4n[1]),
                ("S5", c(s5, m5, "flag"), c(s5, m5, "flag_ctrl")),
                ("S6", int(s6[2]["p"] < sg.ALPHA), int(s6[1]["p"] < sg.ALPHA))):
            rows.append({"half": hf, "detector": det, **sg.decide(f2, f1, sg.ALPHA)})
    dec = pd.DataFrame(rows)
    dec["p_holm"] = np.nan
    for hf in ("D", "C"):
        m = dec["half"] == hf
        dec.loc[m, "p_holm"] = sg.holm(dec.loc[m, "p"].tolist())
    dec["half_ok"] = dec["ratio_ok"] & (dec["p_holm"] < sg.ALPHA)
    both = dec.groupby("detector")["half_ok"].transform("all")
    dec["signature"] = both
    dec.to_csv(OUT / "decision.csv", index=False)

    sec = b.set_index("box")[SEC + ["sha12", "model", "known"]]
    for det, df, cols in (("S1", s1, {"flag": None}), ("S2", s2, {"flag_up": 2, "flag_run_r2": 2, "flag_down": 1,
                                                                    "flag_run_r1": 1}),
                          ("S3", s3, {"flag": None}), ("S5", s5, {"flag": 2, "flag_ctrl": 1})):
        for col, rnd in cols.items():
            hit = df[df[col].fillna(False).astype(bool)]
            for box, r in hit.iterrows():
                flagged.append({"detector": f"{det}:{col}", "rnd": int(r["rnd"]) if rnd is None else rnd,
                                "box": box, "half": r["half"]})
    for _, r in pd.concat(s4_out).iterrows():
        for box in r["boxes"]:
            flagged.append({"detector": "S4", "rnd": r["rnd"], "box": box, "half": r["half"]})
    fl = pd.DataFrame(flagged)
    if len(fl):
        fl = fl.join(sec, on="box")
    fl.to_csv(OUT / "flagged.csv", index=False)
    s1.to_parquet(OUT / "s1.parquet"); s2.to_parquet(OUT / "s2.parquet")
    s3.to_parquet(OUT / "s3.parquet"); s5.to_parquet(OUT / "s5.parquet")
    pd.concat(s4_out).to_csv(OUT / "s4_blocks.csv", index=False)
    (OUT / "s6.json").write_text(json.dumps(s6_out, indent=1, default=str))
    pd.set_option("display.width", 200)
    print(dec.to_string())
    if len(fl):
        print(fl.groupby(["half", "detector", "rnd"]).size().to_string())
    print("done", flush=True)


if __name__ == "__main__":
    main()
