"""H8r2 detectors: parsing, false alarms on clean synthetic data, and power on injected signatures."""
import itertools
import math

import numpy as np
import pandas as pd
import pytest

from tally import signatures as sg

RNG = np.random.default_rng(7)


def fmt(day, s):
    return f"{day} {s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def line(day, t, msg, app="VOTA"):
    return "\t".join([fmt(day, t), "INFO", "67305985", app, msg, "ABCDEF"])


def voter_lines(day, t, bio=True, worker=None, attempts=2, score=None):
    L = [line(day, t, "Aguardando digitação do identificador do eleitor"),
         line(day, t + 10, "Identificador do eleitor digitado pelo mesário"),
         line(day, t + 10, "Identificador digitado pelo mesário foi: (Título de eleitor)"),
         line(day, t + 10, "Foto do eleitor apresentada")]
    for k in range(1, attempts + 1):
        L.append(line(day, t + 12 + k, f"Solicita digital. Tentativa [{k}] de [4]"))
    if score is not None:
        L.append(line(day, t + 18, f"Batimento de digitais retornou o score {score}"))
    if bio:
        L.append(line(day, t + 20, "Tipo de habilitação do eleitor [biométrica]"))
    else:
        L.append(line(day, t + 20, "Solicitação de dado pessoal do eleitor para habilitação manual"))
        if worker:
            L.append(line(day, t + 21, f"Mesário {worker} habilitou o eleitor"))
    L += [line(day, t + 22, "Eleitor foi habilitado"),
          line(day, t + 40, "Tecla indevida pressionada"),
          line(day, t + 41, "Voto confirmado para [Presidente]"),
          line(day, t + 42, "O voto do eleitor foi computado")]
    return L


def test_trails_parse():
    day = "25/10/2026"
    text = "\n".join(voter_lines(day, 30000, score=55) + voter_lines(day, 30100, bio=False, worker="123456789012")
                     + voter_lines(day, 30200, bio=False, worker="123456789012")
                     + [line(day, 30300, "Aguardando digitação do identificador do eleitor"),
                        line(day, 30310, "Justificativa recebida")]
                     + voter_lines("04/10/2026", 30000))
    tr, inc = sg.trails(text, day)
    assert len(tr) == 3 and inc == 1
    a, b, c = tr
    assert (a["bio"], a["attempts"], a["n_scores"], a["score_last"], a["id_type"]) == (1, 2, 1, 55, 0)
    assert a["t_enabled"] == 30022 and a["t_computed"] == 30042 and a["n_confirm"] == 1 and a["bad_keys"] == 1
    assert b["bio"] == 0 and b["worker"] == 1 and c["worker"] == 1      # worker number replaced by an index
    assert "123456789012" not in repr(tr)
    assert len(sg.trails(text, "04/10/2026")[0]) == 1


def test_software_parse():
    msgs = ["Versão da aplicação: 10.11.0.1 - Praia", "Identificação do Modelo de Urna: UE2020",
            "Verificação de assinatura - Etapa [12] - [/dsk/fi/estatico/o00407rj-ce.vsc] - [SUCESSO]",
            "Verificação de assinatura - Etapa [13] - [/dsk/fi/estatico/o00407br-pu.vsc] - [FALHA]"]
    text = "\n".join(line("16/10/2026", 30000 + i, m, "GAP") for i, m in enumerate(msgs))
    text += "\n" + line("01/10/2026", 30000, "Versão da aplicação: 9.0 - old", "GAP")
    s = sg.software(text)
    assert s["version"] == "10.11.0.1 - Praia" and s["model"] == "UE2020"
    assert s["n_checks"] == 2 and s["n_not_success"] == 1
    sp = sg.software(text.replace("o00407rj", "o00407sp"))
    assert sp["fileset"] == s["fileset"]                                 # UF code normalised


def test_p_longest_run_exact():
    for n, m in [(8, 3), (10, 5), (12, 4)]:
        for r in range(1, m + 1):
            hits = sum(sg.longest_run(np.isin(np.arange(n), c)) >= r for c in itertools.combinations(range(n), m))
            assert sg.p_longest_run(n, m, r) == pytest.approx(hits / math.comb(n, m))


def test_fisher_g():
    noise = RNG.normal(size=256)
    assert sg.fisher_g(noise)[1] > 0.01
    wave = np.sin(2 * np.pi * np.arange(256) / 8) + 0.3 * RNG.normal(size=256)
    assert sg.fisher_g(wave)[1] < 1e-10


def synth(n_boxes=300, n=200, rnd_seed=0):
    """Clean voter tables: independent human-like trails."""
    rng = np.random.default_rng(rnd_seed)
    rows = []
    for b in range(n_boxes):
        t = 8 * 3600 + np.cumsum(rng.gamma(2.0, 60, n)).astype(int)
        en = t - rng.integers(10, 60, n)
        dur = 5 + rng.gamma(3.0, 6, n).astype(int)
        bio = (rng.random(n) > 0.08).astype(int)
        rows.append(pd.DataFrame({
            "box": b, "idx": np.arange(n), "t_start": en - rng.integers(15, 60, n), "t_id": en - rng.integers(5, 15, n),
            "t_enabled": en, "t_computed": en + dur, "id_type": (rng.random(n) < 0.2).astype(int), "photo": 1,
            "attempts": rng.integers(1, 4, n), "n_scores": (rng.random(n) < 0.3).astype(int),
            "score_last": rng.integers(20, 120, n), "bio": bio, "worker": np.where(bio == 0, rng.integers(1, 4, n), -1),
            "n_confirm": 1, "bad_keys": rng.integers(0, 3, n)}))
    v = pd.concat(rows, ignore_index=True)
    v["t_computed"] = v.groupby("box")["t_computed"].transform(lambda s: np.maximum.accumulate(s.to_numpy()))
    v["group"] = "XX:1"
    return v


def test_s1_turbo():
    v = synth()
    assert sg.s1_turbo(v)["flag"].sum() <= 1
    bad = v.copy()
    i = bad.index[(bad["box"] == 5)][:40]
    bad.loc[i, "t_computed"] = bad.loc[i, "t_enabled"]                  # 40 votes in zero seconds in one box
    assert sg.s1_turbo(bad).loc[5, "flag"]


def test_s2_zombie():
    v1, v2 = synth(rnd_seed=1), synth(rnd_seed=2)
    r = sg.s2_zombie(v1, v2)
    assert r["flag_up"].sum() <= 1 and r["flag_run_r2"].sum() <= 1
    v2.loc[(v2["box"] == 3) & (v2["idx"].between(150, 189)), "bio"] = 0   # 40 manual enablings in a row
    r = sg.s2_zombie(v1, v2)
    assert r.loc[3, "flag_run_r2"] and r.loc[3, "flag_up"]


def test_s3_periodicity():
    v = synth(n_boxes=100)
    assert sg.s3_periodicity(v)["flag"].sum() <= 1
    m = v["box"] == 9
    v.loc[m, "bio"] = (np.arange(m.sum()) % 5 != 0).astype(int)          # every 5th voter manual
    assert sg.s3_periodicity(v).loc[9, "flag"]


def test_s4_repetition():
    v = synth(n_boxes=100)
    assert len(sg.s4_repetition(v)) == 0
    src = v[(v["box"] == 1) & v["idx"].between(20, 29)].copy()
    tgt = v.index[(v["box"] == 2) & v["idx"].between(50, 59)]
    shift = v.loc[tgt[0], "t_start"] - src["t_start"].iloc[0]
    for c in sg.VOTER_COLS[1:]:
        vals = src[c].to_numpy() + (shift if c.startswith("t_") else 0)
        v.loc[tgt, c] = vals
    rep = sg.s4_repetition(v)
    assert len(rep) >= 1 and rep["boxes"].iloc[0] == [1, 2]


def test_s5_scores():
    v1, v2 = synth(rnd_seed=3), synth(rnd_seed=4)
    assert sg.s5_scores(v1, v2)["flag"].sum() <= 1
    v2.loc[v2["box"] == 4, ["n_scores", "score_last"]] = [1, 77]         # one repeated score for every voter
    assert sg.s5_scores(v1, v2).loc[4, "flag"]


def test_s6_synchrony():
    v = synth(n_boxes=200)
    off = pd.Series(0.0, index=range(200))
    assert sg.s6_synchrony(v, off, shifts=100)["p"] > 0.01
    rows = []
    for b in range(0, 200, 4):                                           # 50 boxes, 8 votes in the same minute
        rows.append(pd.DataFrame({**{c: 0 for c in sg.VOTER_COLS}, "box": b, "idx": 10_000 + np.arange(8),
                                  "t_computed": 15 * 3600 + 30 + np.arange(8), "group": "XX:1"}))
    r = sg.s6_synchrony(pd.concat([v] + rows, ignore_index=True), off, shifts=100)
    assert r["p"] < 0.02 and r["minute"] == 15 * 60


def sections(n_mun=60, per=30, seed=0, homogeneous=False, add=0):
    rng = np.random.default_rng(seed)
    rows = []
    for m in range(n_mun):
        base, swing = rng.uniform(0.3, 0.6), rng.uniform(0.02, 0.1)
        for s in range(per):
            E = int(rng.integers(200, 400))
            p1 = base if homogeneous else np.clip(base + rng.normal(0, 0.06), 0.05, 0.9)
            o = rng.uniform(0.05, 0.1)
            T1 = int(E * 0.8)
            A1 = rng.binomial(T1, p1)
            O = rng.binomial(T1 - A1, o)
            B1 = T1 - A1 - O - 10
            gain = swing if homogeneous else np.clip(swing + rng.normal(0, 0.05), -0.05, 0.3)
            T2 = int(E * 0.82)
            A2 = min(rng.binomial(T2, min(p1 + gain, 0.95)) + add, T2 - 10)
            rows.append({"SG_UF": "XX", "CD_MUNICIPIO": m, "NR_ZONA": 1, "NR_SECAO": s, "E": E, "A1": A1, "B1": B1,
                         "BN1": 10, "T1": T1, "o_1": O, "o_rest": 0, "A2": A2, "B2": T2 - A2 - 8, "BN2": 8, "T2": T2})
    d = pd.DataFrame(rows)
    d["dA"] = d["A2"] - d["A1"]
    d["d"] = d["dA"] / d["E"]
    return d


def test_t1_dispersion():
    nat, hom = sg.t1_dispersion(sections()), sg.t1_dispersion(sections(seed=1, homogeneous=True))
    assert (nat["R"] <= 1).mean() < 0.1 and (hom["R"] <= 1).mean() > 0.3
    assert sg.t1_compare(hom, nat)["signature"] and not sg.t1_compare(nat, nat)["signature"]


def test_t4_uniform_addition():
    clean, added = sg.t4_regression(sections(seed=2)), sg.t4_regression(sections(seed=2, add=15))
    assert sg.t4_compare(added, clean)["signature"] and not sg.t4_compare(clean, clean)["signature"]


def test_t3_same_increment():
    d = sections(seed=3)
    assert sg.t3_same_increment(d, permutations=200)["p"] > 0.01
    d.loc[d["NR_SECAO"] < 15, "A2"] = d.loc[d["NR_SECAO"] < 15, "A1"] + 12   # half the sections: +12 exactly
    assert sg.t3_same_increment(d, permutations=200)["p"] < 0.01


def test_split_ufs():
    ufs = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI",
           "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO", "ZZ"]
    h = sg.split_ufs(ufs)
    assert list(h.values()).count("D") == 13 and h["ZZ"] == "C" and h == sg.split_ufs(ufs)
