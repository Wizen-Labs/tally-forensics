import numpy as np
import pandas as pd

from tally import project

TRUE_A = np.array([0.95, 0.03, 0.55, 0.20, 0.05])   # share of A1, B1, O1, N1, X1 that votes A in round 2
TRUE_B = np.array([0.02, 0.94, 0.30, 0.15, 0.04])


def _rounds(n_mun=150, secs=30, seed=0):
    """Round 1 and round 2 section tables with a known transfer matrix; the South leans A and arrives first."""
    rng = np.random.default_rng(seed)
    ufs = ["PR", "SC", "RS", "BA", "PE", "CE", "SP", "MG", "PA", "GO"]
    r1, r2 = [], []
    for mun in range(n_mun):
        uf = ufs[mun % len(ufs)]
        lean = 0.62 if project.REGION[uf] == "S" else (0.35 if project.REGION[uf] == "NE" else 0.5)
        for k in range(secs):
            aptos = int(rng.integers(250, 400))
            comp = int(rng.binomial(aptos, 0.8))
            pa = np.clip(rng.normal(lean, 0.06), 0.05, 0.95)
            a, b, o, n = rng.multinomial(comp, [pa * 0.88, (1 - pa) * 0.88, 0.08, 0.04])
            x = np.array([a, b, o, n, aptos - comp])
            a2 = rng.binomial(x, TRUE_A).sum()
            b2 = rng.binomial(x - rng.binomial(x, TRUE_A), TRUE_B / (1 - TRUE_A)).sum()
            key = {"SG_UF": uf, "CD_MUNICIPIO": str(mun), "NR_ZONA": "1", "NR_SECAO": str(k),
                   "NR_LOCAL_VOTACAO": str(k // 4), "QT_APTOS": aptos}
            r1.append({**key, "QT_COMPARECIMENTO": comp, "v_22": a, "v_13": b, "v_70": o, "v_blank": n,
                       "DT_BU_RECEBIDO_BRT": pd.Timestamp("2026-10-04 17:00") + pd.Timedelta(minutes=float(rng.uniform(0, 240)))})
            early = project.REGION[uf] == "S"
            t = pd.Timestamp("2026-10-25 17:00") + pd.Timedelta(minutes=float(rng.uniform(0, 60) if early
                                                                            else rng.uniform(30, 240)))
            r2.append({**key, "QT_COMPARECIMENTO": a2 + b2, "v_22": a2, "v_13": b2, "DT_BU_RECEBIDO_BRT": t})
    return pd.DataFrame(r1), pd.DataFrame(r2)


def _setup(seed=0):
    r1, r2 = _rounds(seed=seed)
    df = project.merge_rounds(r1, r2, "22", "13").sort_values("DT_BU_RECEBIDO_BRT").reset_index(drop=True)
    truth = 100 * df["A2"].sum() / (df["A2"].sum() + df["B2"].sum())
    return df, truth


def test_full_data_recovers_the_transfer_matrix():
    df, _ = _setup()
    out = project.predict(df, np.ones(len(df), bool), project.Params(bootstrap=0))
    assert np.allclose(out["beta_BR_A"], TRUE_A, atol=0.05), out["beta_BR_A"]
    assert np.allclose(out["beta_BR_B"], TRUE_B, atol=0.05), out["beta_BR_B"]


def test_projection_beats_biased_raw_count_at_five_percent():
    df, truth = _setup(seed=1)
    mask = np.arange(len(df)) < int(0.05 * len(df))
    assert set(df.loc[mask, "SG_UF"]) <= {"PR", "SC", "RS", "SP", "MG", "GO", "BA", "PE", "CE", "PA"}
    raw_err = abs(project.raw_share(df, mask) - truth)
    res = project.project(df, mask, project.Params(bootstrap=20))
    assert raw_err > 3, raw_err                      # the early count is badly biased
    assert abs(res["share_a"] - truth) < 0.5, (res["share_a"], truth)
    assert res["share_a_lo90"] < res["share_a"] < res["share_a_hi90"]


def test_municipal_model_is_exact_when_complete_and_the_prior_rescues_poor_identification():
    """Worst case: only one region counted, few near-identical municipal aggregates (FINDINGS P2)."""
    df, truth = _setup(seed=3)
    full = project.predict_municipal(df, np.ones(len(df), bool), project.Params(bootstrap=0))
    assert full["A2"] == df["A2"].sum() and full["B2"] == df["B2"].sum()
    mask = np.arange(len(df)) < int(0.05 * len(df))
    bare = project.predict_municipal(df, mask, project.Params(bootstrap=0))
    res = project.predict_municipal(df, mask, project.Params(bootstrap=0, neutral_prior_sections=500),
                                   min_frac_corr=0.5)
    assert abs(bare["share_a"] - truth) > 3 * abs(res["share_a"] - truth), (bare["share_a"], res["share_a"], truth)
    assert abs(res["share_a"] - truth) < 1.5, (res["share_a"], truth)


def test_unmatched_round2_sections_are_still_counted():
    df, _ = _setup(seed=2)
    df.loc[df.index[-5:], project.GROUPS] = np.nan
    df["matched"] = df[project.GROUPS].notna().all(axis=1)
    out = project.predict(df, np.ones(len(df), bool), project.Params(bootstrap=0))
    assert out["A2"] == df["A2"].sum() and out["B2"] == df["B2"].sum()
