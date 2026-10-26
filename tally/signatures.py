"""H8r2: signature search in the box logs (S1-S7) and in the section-level vote transfer (T1-T4).

Protocol: PREREGISTRATION_ROUND2_SIGNATURES.md. The log detectors are computed for round 2 and, in the same way with
round 1's own reference, for round 1 of the same boxes; round 1 is the control. The transfer tests use 2022 (round 1
to round 2, same sections) as the control. A detected signature is an "unexplained pattern", never a finding of
fraud.

Personal data: the log names poll workers by voter number. Those numbers are mapped to a per-box index (1, 2, ...)
while a log is read and are never stored.
"""
from __future__ import annotations

import hashlib
import io
import math
import re
import zipfile

import numpy as np
import pandas as pd
from scipy import stats

DAYS = {1: "04/10/2026", 2: "25/10/2026"}
LOAD_FROM, LOAD_TO = "20261005", "20261025"    # the round-2 software load happens between the rounds
SEED = 20261026
ALPHA = 0.01

# Log messages (latin1 text, prefix match)
WAIT = "Aguardando digita"                    # "Aguardando digitação do identificador do eleitor"
ID_TYPED = "Identificador do eleitor digitado"
ID_TYPE = "Identificador digitado pelo mes"   # "... foi: (Título de eleitor)" or "(CPF)"
PHOTO = "Foto do eleitor apresentada"
FP_ASK = "Solicita digital. Tentativa ["
SCORE = "Batimento de digitais retornou o score "
ENABLE_TYPE = "Tipo de habilita"              # "Tipo de habilitação do eleitor [biométrica]"
MANUAL_ASK = "Solicita"                       # "Solicitação de dado pessoal do eleitor para habilitação manual"
WORKER = re.compile(r"^Mes\S+ (\d+) habilitou o eleitor")
ENABLED = "Eleitor foi habilitado"
CONFIRM = "Voto confirmado para ["
BAD_KEY = "Tecla indevida pressionada"
COMPUTED = "O voto do eleitor foi computado"
VERSION = "Vers"                              # "Versão da aplicação: ..."
MODEL = "Identifica"                          # "Identificação do Modelo de Urna: UEnnnn"
SIGCHECK = re.compile(r"^Verifica\S+ de assinatura - Etapa \[\d+\] - \[([^\]]*)\] - \[?([A-Z]*)")

VOTER_COLS = ["idx", "t_start", "t_id", "t_enabled", "t_computed", "id_type", "photo", "attempts", "n_scores",
              "score_last", "bio", "worker", "n_confirm", "bad_keys"]


def _sec(ts: str) -> int:
    return int(ts[11:13]) * 3600 + int(ts[14:16]) * 60 + int(ts[17:19])


def _new(idx: int, t: int) -> dict:
    return {"idx": idx, "t_start": t, "t_id": -1, "t_enabled": -1, "t_computed": -1, "id_type": -1, "photo": 0,
            "attempts": 0, "n_scores": 0, "score_last": -1, "bio": -1, "worker": -1, "n_confirm": 0, "bad_keys": 0}


def read_log(jez: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(jez)) as z:
        name = next(n for n in z.namelist() if n.endswith(".dat"))
        return z.read(name).decode("latin1")


def trails(text: str, day: str) -> tuple[list[dict], int]:
    """Per-voter trails of one voting day, in order. Returns (complete trails, number of trails that never reached
    'O voto do eleitor foi computado'). Times are seconds since local midnight on the box clock."""
    out, cur, incomplete, workers = [], None, 0, {}
    for line in text.splitlines():
        if not line.startswith(day):
            continue
        f = line.split("\t")
        if len(f) < 5:
            continue
        t, msg = _sec(f[0]), f[4]
        if msg.startswith(WAIT):
            if cur is not None:
                incomplete += 1
            cur = _new(len(out), t)
            continue
        if cur is None:
            if not (msg.startswith(ENABLED) or msg.startswith(ENABLE_TYPE) or msg.startswith(CONFIRM)
                    or msg.startswith(COMPUTED)):
                continue
            cur = _new(len(out), -1)
        if msg.startswith(ID_TYPED):
            cur["t_id"] = t
        elif msg.startswith(ID_TYPE):
            cur["id_type"] = 1 if "CPF" in msg else 0 if "tulo" in msg else 2
        elif msg.startswith(PHOTO):
            cur["photo"] = 1
        elif msg.startswith(FP_ASK):
            try:
                cur["attempts"] = max(cur["attempts"], int(msg[len(FP_ASK):].split("]")[0]))
            except ValueError:
                pass
        elif msg.startswith(SCORE):
            cur["n_scores"] += 1
            try:
                cur["score_last"] = int(msg[len(SCORE):].split()[0])
            except (ValueError, IndexError):
                pass
        elif msg.startswith(ENABLE_TYPE):
            cur["bio"] = 1 if "biom" in msg else 0
        elif msg.startswith(MANUAL_ASK) and "manual" in msg:
            if cur["bio"] != 1:
                cur["bio"] = 0
        elif (m := WORKER.match(msg)):
            cur["worker"] = workers.setdefault(m.group(1), len(workers) + 1)
        elif msg.startswith(ENABLED):
            cur["t_enabled"] = t
        elif msg.startswith(CONFIRM):
            cur["n_confirm"] += 1
        elif msg.startswith(BAD_KEY):
            cur["bad_keys"] += 1
        elif msg.startswith(COMPUTED):
            cur["t_computed"] = t
            cur["idx"] = len(out)
            out.append(cur)
            cur = None
    if cur is not None:
        incomplete += 1
    return out, incomplete


def software(text: str) -> dict:
    """S7 features from the round-2 software load (lines dated between the rounds, and the round-2 day)."""
    versions, models, files, results = set(), set(), set(), []
    for line in text.splitlines():
        f = line.split("\t")
        if len(f) < 5 or len(f[0]) < 10:
            continue
        d = f[0][6:10] + f[0][3:5] + f[0][0:2]
        if not (LOAD_FROM <= d <= LOAD_TO):
            continue
        msg = f[4]
        if msg.startswith(VERSION) and ":" in msg:
            versions.add(msg.split(":", 1)[1].strip())
        elif msg.startswith(MODEL) and "Modelo" in msg:
            models.add(msg.split(":", 1)[1].strip())
        elif (m := SIGCHECK.match(msg)):
            files.add(re.sub(r"(?<=#####)(?!br)[a-z]{2}(?=-)", "uf", re.sub(r"\d", "#", m.group(1))))
            results.append(m.group(2) or "?")
    fileset = hashlib.sha1("\n".join(sorted(files)).encode()).hexdigest()[:12]
    return {"version": "|".join(sorted(versions)), "model": "|".join(sorted(models)), "fileset": fileset,
            "n_checks": len(results), "n_not_success": sum(r != "SUCESSO" for r in results)}


def box_record(jez: bytes) -> tuple[dict[int, pd.DataFrame], dict]:
    """Voter tables for both rounds plus the box-level record (S7 features, incomplete trails)."""
    text = read_log(jez)
    voters, box = {}, software(text)
    for rnd, day in DAYS.items():
        tr, inc = trails(text, day)
        voters[rnd] = pd.DataFrame(tr, columns=VOTER_COLS).astype("int32")
        box[f"votes_r{rnd}"], box[f"incomplete_r{rnd}"] = len(tr), inc
    return voters, box


# ---------------------------------------------------------------- helpers

def split_ufs(ufs: list[str], seed: int = SEED) -> dict[str, str]:
    """Discovery half D and confirmation half C; abroad (ZZ) goes to C."""
    br = sorted(u.upper() for u in ufs if u.upper() != "ZZ")
    order = np.random.default_rng(seed).permutation(len(br))
    half = {br[i]: ("D" if k < len(br) // 2 else "C") for k, i in enumerate(order)}
    half["ZZ"] = "C"
    return half


def bonferroni_flags(p: np.ndarray, alpha: float = ALPHA) -> np.ndarray:
    p = np.asarray(p, float)
    n = np.isfinite(p).sum()
    return np.isfinite(p) & (p < alpha / max(n, 1))


def decide(flag_r2: int, flag_ctrl: int, expected: float) -> dict:
    """Decision rule of §3 for one detector in one half: flagged count at least 2x the null expectation and 2x the
    control, and an excess over the control with one-sided binomial p (p is Holm-adjusted by the caller)."""
    n = flag_r2 + flag_ctrl
    p = stats.binomtest(flag_r2, n, 0.5, alternative="greater").pvalue if n else 1.0
    big = flag_r2 >= 2 * max(expected, 1e-9) and flag_r2 >= 2 * flag_ctrl and flag_r2 > 0
    return {"flagged": int(flag_r2), "control": int(flag_ctrl), "expected": float(expected), "p": float(p),
            "ratio_ok": bool(big)}


def holm(p: list[float]) -> list[float]:
    p = np.asarray(p, float)
    order = np.argsort(p)
    adj = np.empty_like(p)
    run = 0.0
    for rank, i in enumerate(order):
        run = max(run, (len(p) - rank) * p[i])
        adj[i] = min(run, 1.0)
    return adj.tolist()


# ---------------------------------------------------------------- S1-S6 (one round's voter table)
# A voter table `v` has the columns of VOTER_COLS plus "box" (an integer id) and "group" (UF and ballot).

def ballot_group(v: pd.DataFrame, uf: pd.Series) -> pd.Series:
    """Reference group: UF and the box's modal number of offices confirmed per voter."""
    modal = v.groupby("box")["n_confirm"].agg(lambda s: s.mode().iloc[0])
    return uf.astype(str) + ":" + v["box"].map(modal).astype(str)


def s1_turbo(v: pd.DataFrame, q: float = 0.001) -> pd.DataFrame:
    """Votes whose 'enabled -> computed' time is at or below the round's q-quantile in the box's group, more
    concentrated in one box than binomial chance allows."""
    ok = (v["t_enabled"] >= 0) & (v["t_computed"] >= v["t_enabled"])
    d = v.loc[ok, ["box", "group"]].assign(dur=(v["t_computed"] - v["t_enabled"])[ok])
    thr = d.groupby("group")["dur"].quantile(q)
    d["fast"] = d["dur"] <= d["group"].map(thr)
    p0 = d.groupby("group")["fast"].mean()
    b = d.groupby("box").agg(n=("fast", "size"), k=("fast", "sum"), group=("group", "first"))
    b["p0"] = b["group"].map(p0)
    b["p"] = stats.binom.sf(b["k"] - 1, b["n"], b["p0"])
    b["flag"] = bonferroni_flags(b["p"].to_numpy())
    return b


def longest_run(x: np.ndarray) -> int:
    best = cur = 0
    for e in x:
        cur = cur + 1 if e else 0
        best = max(best, cur)
    return best


def p_longest_run(n: int, m: int, r: int) -> float:
    """P(longest run of ones >= r) for a random arrangement of m ones among n positions (exact)."""
    if r <= 0 or m == 0:
        return 1.0 if r <= 0 else 0.0
    if r > m:
        return 0.0
    k = n - m                                             # zeros
    below = 0                                             # arrangements with every run < r
    for j in range(0, m // r + 1):
        below += (-1) ** j * math.comb(k + 1, j) * math.comb(m - j * r + k, k)
    return 1.0 - below / math.comb(n, m)


def s2_zombie(v1: pd.DataFrame, v2: pd.DataFrame) -> pd.DataFrame:
    """(a) manual enablings, round 2 vs round 1 of the same box (one-sided Fisher), with the reverse direction as
    the control; (b) the longest run of consecutive manual enablings in each round, against random order;
    (c) the largest number of voters enabled by one poll worker (descriptive)."""
    def per_box(v):
        e = v[v["bio"] >= 0]
        g = e.groupby("box")
        out = pd.DataFrame({"n": g.size(), "m": g["bio"].apply(lambda s: int((s == 0).sum()))})
        out["run"] = g["bio"].apply(lambda s: longest_run((s.to_numpy() == 0)))
        out["worker_max"] = v[v["worker"] > 0].groupby(["box", "worker"]).size().groupby("box").max()
        out["worker_max"] = out["worker_max"].fillna(0).astype(int)
        out["p_run"] = [p_longest_run(int(n), int(m), int(r)) for n, m, r in zip(out["n"], out["m"], out["run"])]
        return out

    a, b = per_box(v1), per_box(v2)
    j = a.join(b, lsuffix="_r1", rsuffix="_r2", how="inner")
    up, down = [], []
    for m1, n1, m2, n2 in zip(j["m_r1"], j["n_r1"], j["m_r2"], j["n_r2"]):
        tab = [[m2, n2 - m2], [m1, n1 - m1]]
        up.append(stats.fisher_exact(tab, alternative="greater")[1])
        down.append(stats.fisher_exact(tab, alternative="less")[1])
    j["p_up"], j["p_down"] = up, down
    j["flag_up"] = bonferroni_flags(j["p_up"].to_numpy())
    j["flag_down"] = bonferroni_flags(j["p_down"].to_numpy())
    j["flag_run_r1"] = bonferroni_flags(j["p_run_r1"].to_numpy())
    j["flag_run_r2"] = bonferroni_flags(j["p_run_r2"].to_numpy())
    return j


def fisher_g(x: np.ndarray) -> tuple[float, float]:
    """Fisher's g test for one dominant period in a series (exact p-value)."""
    x = np.asarray(x, float)
    x = x - x.mean()
    spec = np.abs(np.fft.rfft(x)[1:]) ** 2
    if len(x) % 2 == 0:
        spec = spec[:-1]
    m = len(spec)
    if m < 2 or spec.sum() <= 0:
        return float("nan"), float("nan")
    g = spec.max() / spec.sum()
    p = 0.0
    for j in range(1, int(1 / g) + 1):
        p += (-1) ** (j - 1) * math.comb(m, j) * (1 - j * g) ** (m - 1)
    return float(g), float(min(max(p, 0.0), 1.0))


def _detrend(x: np.ndarray, w: int = 15) -> np.ndarray:
    s = pd.Series(x, dtype=float)
    return (s - s.rolling(w, center=True, min_periods=1).mean()).to_numpy()


def s3_periodicity(v: pd.DataFrame, min_n: int = 64) -> pd.DataFrame:
    """Fisher's g on three voter-level series per box: log inter-vote interval (detrended), enabling type and
    fingerprint attempts. Bonferroni over boxes x series."""
    rows = []
    for box, s in v.sort_values(["box", "t_computed"]).groupby("box"):
        if len(s) < min_n:
            continue
        gap = np.log1p(np.diff(s["t_computed"].to_numpy()).clip(min=0))
        out = {"box": box, "n": len(s)}
        for name, x in (("gap", _detrend(gap)), ("bio", s["bio"].to_numpy()), ("attempts", s["attempts"].to_numpy())):
            out[f"g_{name}"], out[f"p_{name}"] = fisher_g(x) if np.ptp(x) > 0 else (np.nan, np.nan)
        rows.append(out)
    b = pd.DataFrame(rows).set_index("box") if rows else pd.DataFrame()
    if len(b):
        p = b[["p_gap", "p_bio", "p_attempts"]].to_numpy()
        n = np.isfinite(p).sum()
        b["flag"] = (np.nan_to_num(p, nan=1.0) < ALPHA / max(n, 1)).any(axis=1)
    return b


def s4_repetition(v: pd.DataFrame, block: int = 10) -> pd.DataFrame:
    """Blocks of `block` consecutive voter trails identical in event codes and intervals, found in two or more
    different boxes. Vectorised 64-bit rolling hash; returns one row per repeated block hash with its boxes."""
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
            return pd.DataFrame(columns=["hash", "n_boxes", "boxes"])
        H = np.zeros(n, dtype=np.uint64)
        for k in range(block):
            H = H * np.uint64(1099511628211) + h[k:k + n]
    box = s["box"].to_numpy()
    same = box[:n] == box[block - 1:block - 1 + n]
    h_df = pd.DataFrame({"hash": H[same], "box": box[:n][same]}).drop_duplicates()
    cnt = h_df.groupby("hash")["box"].nunique()
    rep = h_df[h_df["hash"].isin(cnt[cnt >= 2].index)]
    out = rep.groupby("hash")["box"].agg(n_boxes="nunique", boxes=lambda x: sorted(x.tolist())).reset_index()
    out["hash"] = out["hash"].map(lambda x: f"{int(x):016x}")
    return out


def s5_scores(v1: pd.DataFrame, v2: pd.DataFrame, min_n: int = 20) -> pd.DataFrame:
    """Chi-square of each box's round-2 fingerprint scores against its round-1 scores, on decile bins of the
    national round-1 scores. Control: the same test between round-1 even- and odd-numbered voters."""
    s1, s2 = v1[v1["n_scores"] > 0], v2[v2["n_scores"] > 0]
    if s1.empty:
        return pd.DataFrame()
    edges = np.unique(np.quantile(s1["score_last"], np.linspace(0, 1, 11)))
    edges[0], edges[-1] = -np.inf, np.inf

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
    out = pd.DataFrame(rows).set_index("box") if rows else pd.DataFrame(columns=["p", "p_ctrl"])
    out["flag"] = bonferroni_flags(out["p"].to_numpy())
    out["flag_ctrl"] = bonferroni_flags(out["p_ctrl"].to_numpy())
    return out


def s6_synchrony(v: pd.DataFrame, offset_h: pd.Series, shifts: int = 200, p_spike: float = 1e-6,
                 seed: int = SEED) -> dict:
    """Per box, minutes (BRT) whose vote count is a Poisson outlier against the box's own rate over its open span;
    then the largest number of boxes spiking in the same clock minute, against random circular shifts of each
    box's spikes within its own span. `offset_h` maps box -> hours to add to the box clock to get BRT."""
    t = v["t_computed"] + v["box"].map(offset_h) * 3600
    d = v.assign(minute=(t // 60)).dropna(subset=["minute"])
    d["minute"] = d["minute"].astype(int)
    spikes = []                                          # (box, minute, span_start, span_len)
    for box, s in d.groupby("box"):
        cnt = s["minute"].value_counts()
        lo, hi = s["minute"].min(), s["minute"].max()
        span = hi - lo + 1
        if span < 30:
            continue
        lam = len(s) / span
        thr = stats.poisson.isf(p_spike, lam) + 1
        for mnt in cnt[cnt >= thr].index:
            spikes.append((box, mnt, lo, span))
    if not spikes:
        return {"max_sync": 0, "minute": None, "p": 1.0, "n_spikes": 0}
    sp = pd.DataFrame(spikes, columns=["box", "minute", "lo", "span"])
    obs = sp.groupby("minute")["box"].nunique()
    best = int(obs.max())
    rng = np.random.default_rng(seed)
    ge = 0
    boxes = pd.factorize(sp["box"])[0]
    box_span = sp.groupby(boxes)["span"].first().to_numpy()
    for _ in range(shifts):
        shift = rng.integers(0, box_span)[boxes]
        m = sp["lo"].to_numpy() + (sp["minute"].to_numpy() - sp["lo"].to_numpy() + shift) % sp["span"].to_numpy()
        ge += np.bincount(m - m.min()).max() >= best
    return {"max_sync": best, "minute": int(obs.idxmax()), "p": (ge + 1) / (shifts + 1), "n_spikes": len(sp)}


def s7_software(boxes: pd.DataFrame) -> pd.DataFrame:
    """Boxes whose version or set of signature-checked files differs from their model's mode, or with any check
    that did not report SUCESSO. Deterministic; every row returned is listed."""
    b = boxes.copy()
    key = b["version"] + "/" + b["fileset"]
    mode = key.groupby(b["model"]).agg(lambda s: s.mode().iloc[0])
    b["differs"] = key != b["model"].map(mode)
    return b[b["differs"] | (b["n_not_success"] > 0) | (b["n_checks"] == 0)]


# ---------------------------------------------------------------- T1-T4 (section transfers)

KEY = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
MUN = ["SG_UF", "CD_MUNICIPIO"]


def transfer_frame(r1: pd.DataFrame, r2: pd.DataFrame, nr_a: str, nr_b: str, top_others: int = 4,
                   min_electorate: int = 50) -> pd.DataFrame:
    """One row per section in both rounds (aggregated sections excluded): electorate, both rounds' votes for A and
    B, the other candidates of round 1 (the `top_others` largest separately, the rest pooled), blank+null, turnout,
    and d = (A2 - A1) / electorate."""
    cand = [c for c in r1.columns if c.startswith("v_") and c[2:].isdigit() and c not in (f"v_{nr_a}", f"v_{nr_b}")]
    top = r1[cand].sum().sort_values(ascending=False).index[:top_others].tolist()
    a = r1[~r1["aggregated"]][KEY + [f"v_{nr_a}", f"v_{nr_b}", "v_blank", "v_null", "QT_COMPARECIMENTO"] + cand]
    a = a.assign(o_rest=a[[c for c in cand if c not in top]].sum(axis=1))
    a = a.rename(columns={f"v_{nr_a}": "A1", f"v_{nr_b}": "B1", "QT_COMPARECIMENTO": "T1",
                          **{c: f"o_{c[2:]}" for c in top}})
    a["BN1"] = a["v_blank"] + a["v_null"]
    b = r2[~r2["aggregated"]][KEY + [f"v_{nr_a}", f"v_{nr_b}", "v_blank", "v_null", "QT_COMPARECIMENTO", "QT_APTOS"]
                              + (["extended"] if "extended" in r2.columns else [])]
    b = b.rename(columns={f"v_{nr_a}": "A2", f"v_{nr_b}": "B2", "QT_COMPARECIMENTO": "T2", "QT_APTOS": "E"})
    b["BN2"] = b["v_blank"] + b["v_null"]
    keep = KEY + ["A1", "B1", "BN1", "T1", "o_rest"] + [f"o_{c[2:]}" for c in top]
    d = a[keep].merge(b.drop(columns=["v_blank", "v_null"]), on=KEY)
    d = d[d["E"] >= min_electorate].reset_index(drop=True)
    d["dA"] = d["A2"] - d["A1"]
    d["d"] = d["dA"] / d["E"]
    return d


def t1_dispersion(d: pd.DataFrame, min_sections: int = 10) -> pd.DataFrame:
    """Per municipality: R = variance of d / mean binomial variance of d. R <= 1 means the sections differ no more
    than identical coins would."""
    g = d.assign(p1=d["A1"] / d["E"], p2=d["A2"] / d["E"]).groupby(MUN)
    m = g.agg(n=("d", "size"), var_d=("d", "var"), p1=("p1", "mean"), p2=("p2", "mean"), inv_e=("E", lambda e: (1 / e).mean()))
    m = m[m["n"] >= min_sections]
    m["binvar"] = (m["p1"] * (1 - m["p1"]) + m["p2"] * (1 - m["p2"])) * m["inv_e"]
    m["R"] = m["var_d"] / m["binvar"]
    return m


def t1_compare(m26: pd.DataFrame, m22: pd.DataFrame) -> dict:
    k1, n1 = int((m26["R"] <= 1).sum()), len(m26)
    k0, n0 = int((m22["R"] <= 1).sum()), len(m22)
    p1, p0 = k1 / n1, k0 / n0
    pool = (k1 + k0) / (n1 + n0)
    se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n0)) if 0 < pool < 1 else float("nan")
    p = float(stats.norm.sf((p1 - p0) / se)) if se == se and se > 0 else 1.0
    return {"share_2026": p1, "share_2022": p0, "n_2026": n1, "n_2022": n0, "p": p,
            "signature": bool(p1 >= 2 * p0 and p1 > 0 and p < ALPHA)}


def t4_regression(d: pd.DataFrame) -> dict:
    """OLS of A2 - A1 on electorate, each other candidate's round-1 votes, the fall in blank+null and the change in
    turnout, with errors clustered by municipality. The intercept is a uniform additive increase per box."""
    others = [c for c in d.columns if c.startswith("o_")]
    X = np.column_stack([np.ones(len(d)), d["E"], *(d[c] for c in others), d["BN1"] - d["BN2"], d["T2"] - d["T1"]])
    names = ["const", "E", *others, "blank_null_fall", "turnout_change"]
    y = d["dA"].to_numpy(float)
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    resid = y - X @ beta
    cl = pd.factorize(d["SG_UF"].astype(str) + d["CD_MUNICIPIO"].astype(str))[0]
    scores = pd.DataFrame(X * resid[:, None]).groupby(cl).sum().to_numpy()
    meat = scores.T @ scores
    G, n, k = len(scores), len(y), X.shape[1]
    V = XtX_inv @ meat @ XtX_inv * (G / (G - 1)) * ((n - 1) / (n - k))
    se = np.sqrt(np.diag(V))
    return {"coef": dict(zip(names, beta.tolist())), "se": dict(zip(names, se.tolist())), "resid": resid}


def t4_compare(r26: dict, r22: dict) -> dict:
    a, b = r26["coef"]["const"], r22["coef"]["const"]
    se = math.hypot(r26["se"]["const"], r22["se"]["const"])
    z = stats.norm.ppf(1 - ALPHA / 2)
    lo, hi = (a - b) - z * se, (a - b) + z * se
    return {"a_2026": a, "a_2022": b, "diff_ci99": (lo, hi), "signature": bool(a > 0 and lo > 0)}


def densest_share(x: np.ndarray, width: float) -> float:
    x = np.sort(x[np.isfinite(x)])
    if len(x) == 0:
        return float("nan")
    j = np.searchsorted(x, x + width, side="right")
    return float((j - np.arange(len(x))).max() / len(x))


def t2_spike(d26: pd.DataFrame, res26: np.ndarray, d22: pd.DataFrame, res22: np.ndarray, width_pp: float = 0.5,
             boots: int = 500, seed: int = SEED) -> dict:
    """Share of sections inside the densest `width_pp` window of the T4 residuals (in pp of the electorate), 2026 vs
    2022, with a bootstrap over municipalities."""
    def share(d, res, idx=None):
        x = 100 * res / d["E"].to_numpy()
        return densest_share(x if idx is None else x[idx], width_pp)

    def groups(d):
        return pd.factorize(d["SG_UF"].astype(str) + d["CD_MUNICIPIO"].astype(str))[0]

    s26, s22 = share(d26, res26), share(d22, res22)
    g26, g22 = groups(d26), groups(d22)
    rng = np.random.default_rng(seed)
    idx26 = [np.flatnonzero(g26 == g) for g in range(g26.max() + 1)]
    idx22 = [np.flatnonzero(g22 == g) for g in range(g22.max() + 1)]
    worse = 0
    for _ in range(boots):
        b26 = np.concatenate([idx26[i] for i in rng.integers(0, len(idx26), len(idx26))])
        b22 = np.concatenate([idx22[i] for i in rng.integers(0, len(idx22), len(idx22))])
        worse += share(d26, res26, b26) <= share(d22, res22, b22)
    p = (worse + 1) / (boots + 1)
    return {"share_2026": s26, "share_2022": s22, "ratio": s26 / s22 if s22 else float("nan"), "p": p,
            "signature": bool(s22 > 0 and s26 >= 1.5 * s22 and p < ALPHA)}


def t3_same_increment(d: pd.DataFrame, permutations: int = 1000, seed: int = SEED) -> dict:
    """Sections whose A2 - A1 equals their municipality's modal increment. Null: the relative change (A2 - A1) / A1
    is permuted among sections of the same municipality and similar size (electorate within one 5% log-bin) and
    applied to each section's own A1, so the link between a section's two rounds is kept and only exact
    coincidences of the increment are tested."""
    mun = pd.factorize(d["SG_UF"].astype(str) + d["CD_MUNICIPIO"].astype(str))[0]
    size_bin = np.floor(np.log(d["E"].to_numpy()) / np.log(1.05)).astype(np.int64)
    cell = pd.factorize(mun.astype(np.int64) * 10_000 + size_bin)[0]
    a1, a2 = d["A1"].to_numpy(np.int64), d["A2"].to_numpy(np.int64)
    rel = (a2 - a1) / np.maximum(a1, 1)

    def count(a2v):
        inc = a2v - a1
        key = mun.astype(np.int64) * 1_000_000 + (inc - inc.min())
        _, first, c = np.unique(key, return_index=True, return_counts=True)
        return int(pd.Series(c).groupby(mun[first]).max().sum())

    obs = count(a2)
    rng = np.random.default_rng(seed)
    base = np.argsort(cell, kind="stable")
    sims = np.empty(permutations, dtype=np.int64)
    for i in range(permutations):
        perm = np.lexsort((rng.random(len(cell)), cell))
        relp = np.empty_like(rel)
        relp[base] = rel[perm]
        sims[i] = count(a1 + np.rint(relp * np.maximum(a1, 1)).astype(np.int64))
    return {"observed": obs, "perm_mean": float(sims.mean()),
            "excess_ratio": obs / sims.mean() if sims.mean() else float("nan"),
            "p": float((1 + (sims >= obs).sum()) / (1 + permutations))}


def fingerprint(d: pd.DataFrame, share_col: str, turnout_col: str, bins: int = 100) -> np.ndarray:
    """Turnout x share 2D histogram (Klimek et al. 2012), weighted by electorate. Descriptive only."""
    h, _, _ = np.histogram2d(d[turnout_col].clip(0, 1), d[share_col].clip(0, 1), bins=bins, range=[[0, 1], [0, 1]],
                             weights=d["E"])
    return h
