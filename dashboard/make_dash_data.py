"""Builds the public-dashboard datasets (audit / phase 1 only) from the project's own results."""
import json
import os
import sys
from pathlib import Path

os.chdir(r"C:\Users\USER\cloude_cloud\tally-forensics-kit")
sys.path.insert(0, os.getcwd())
import numpy as np
import pandas as pd
from tally import INTERIM_DIR
from tally.load import add_shares

OUT = Path(__file__).resolve().parent / "data"
OUT.mkdir(exist_ok=True)
REP = Path("reports/2026_t1_20261011-133033")
summary = json.loads((REP / "summary.json").read_text(encoding="utf-8"))
integ = pd.read_csv(REP / "integrity.csv")
wt = pd.read_csv(REP / "window_tests.csv")


def dump(name, rows):
    (OUT / f"{name}.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    print(name, len(rows), "rows", (OUT / f"{name}.json").stat().st_size, "bytes")


# per-minute receptions (Brazil only) and pauses
def per_minute(year):
    s = pd.read_parquet(INTERIM_DIR / f"sections_{year}_t1.parquet", columns=["SG_UF", "DT_BU_RECEBIDO_BRT"])
    t = s.loc[s["SG_UF"] != "ZZ", "DT_BU_RECEBIDO_BRT"].dropna()
    return t.dt.strftime("%H:%M").value_counts()


m26, m22 = per_minute(2026), per_minute(2022)
clock = pd.date_range("2026-10-04 17:00", "2026-10-04 21:30", freq="min").strftime("%H:%M")
reception = [{"clock": c, "y2026": int(m26.get(c, 0)), "y2022": int(m22.get(c, 0))} for c in clock]
dump("reception", reception)


def runs(counts, label):
    out, start = [], None
    for c in clock:
        n = counts.get(c, 0)
        if n == 0 and start is None:
            start = c
        elif n > 0 and start is not None:
            k = int((pd.Timestamp(f"2000-01-01 {c}") - pd.Timestamp(f"2000-01-01 {start}")).total_seconds() // 60)
            if k >= 2 and start != clock[0]:          # the minutes before the first reception are not a pause
                out.append({"election": label, "start": start, "end": c, "minutes": k})
            start = None
    return out


# only pauses before 99.5% received are meaningful (late tail has natural zeros)
def cutoff(year):
    s = pd.read_parquet(INTERIM_DIR / f"sections_{year}_t1.parquet", columns=["SG_UF", "DT_BU_RECEBIDO_BRT"])
    t = s.loc[s["SG_UF"] != "ZZ", "DT_BU_RECEBIDO_BRT"].dropna().sort_values()
    return t.iloc[int(0.995 * (len(t) - 1))].strftime("%H:%M")


c26, c22 = cutoff(2026), cutoff(2022)
pauses = [r for r in runs(m26, "1Âº turno 2026") if r["start"] < c26] + [r for r in runs(m22, "1Âº turno 2022") if r["start"] < c22]
dump("pauses", pauses)

# headline figures
viol = dict(zip(integ["check"], integ["violations"]))
kpis = [
    {"metric": "urnas_periciadas", "value": int(summary["sections_counted"])},
    {"metric": "votos_flavio", "value": 56104503},
    {"metric": "votos_lula", "value": 53879538},
    {"metric": "diferenca_soma_boletins_flavio", "value": int(viol["R-22"])},
    {"metric": "diferenca_soma_boletins_lula", "value": int(viol["R-13"])},
    {"metric": "efeito_teste_principal_pp", "value": round(100 * summary["primary_test"]["effect"], 3)},
    {"metric": "p_teste_principal", "value": round(summary["primary_test"]["p_value"], 2)},
    {"metric": "locais_comparados", "value": int(summary["primary_test"]["informative_locations"])},
    {"metric": "maior_pausa_2026_min", "value": max(p["minutes"] for p in pauses if "2026" in p["election"])},
    {"metric": "maior_pausa_2022_min", "value": max(p["minutes"] for p in pauses if "2022" in p["election"])},
]
dump("kpis", kpis)

# window tests (adjusted margin = the pre-registered primary metric)
names = {"primary: freeze window": "Janela do travamento (19h00â€“20h08)",
         "sensitivity: start -15 min": "Sensibilidade: inÃ­cio 15 min antes",
         "sensitivity: start +15 min": "Sensibilidade: inÃ­cio 15 min depois",
         "sensitivity: end +15 min": "Sensibilidade: fim 15 min depois",
         "placebo 17:52-19:00": "Placebo 17h52â€“19h00",
         "placebo 20:08-21:16": "Placebo 20h08â€“21h16"}
w = wt[wt["metric"] == "margin_resid_adj"]
tests = [{"janela": names[r.window], "papel": {"primary": "principal", "sensitivity": "sensibilidade",
                                               "placebo": "placebo"}[r.role],
          "efeito_pp": round(100 * r.effect, 3), "p": round(r.p_value, 4), "locais": int(r.informative_locations)}
         for r in w.itertuples()]
dump("window_tests", tests)

# integrity checks
pt = {"I1": "Votos para presidente = eleitores que compareceram", "I2": "Aptos = compareceram + faltaram",
      "I3": "Nenhuma seÃ§Ã£o com mais votantes que eleitores", "I4": "Nenhuma seÃ§Ã£o repetida",
      "I5": "Nenhuma urna fÃ­sica usada em duas seÃ§Ãµes", "I6": "HorÃ¡rios em ordem (abriu, fechou, emitiu, recebido)",
      "I6b": "SeÃ§Ãµes sem horÃ¡rio de abertura (informativo)", "I7": "Nenhum boletim recebido antes das 17h",
      "R-22": "Soma dos boletins = total oficial de FlÃ¡vio", "R-13": "Soma dos boletins = total oficial de Lula"}
integrity = [{"verificacao": r.check, "descricao": pt[r.check], "testado": int(r.tested), "violacoes": int(r.violations)}
             for r in integ.itertuples()]
dump("integrity", integrity)

# fingerprint: 2% bins of turnout (40-100) x share (0-100), both candidates
s = pd.read_parquet(INTERIM_DIR / "sections_2026_t1.parquet")
s = add_shares(s[(s["SG_UF"] != "ZZ") & (s["CD_TIPO_URNA"] == 1)], "22", "13")
s = s[s["valid"] >= 30]
fp = []
for col, name in (("share_a", "FlÃ¡vio Bolsonaro"), ("share_b", "Lula")):
    tb = np.clip((s["turnout"] * 100 // 2) * 2, 40, 98)
    sb = np.clip((s[col] * 100 // 2) * 2, 0, 98)
    g = pd.DataFrame({"t": tb, "s": sb}).value_counts().reset_index(name="n")
    fp += [{"candidato": name, "comparecimento": int(r.t), "votos": int(r.s), "secoes": int(r.n)} for r in g.itertuples()]
dump("fingerprint", fp)

