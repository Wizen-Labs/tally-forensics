"""Deterministic consistency checks. Unlike the statistical tests, a violation here is a fact, not a signal."""

import pandas as pd

POLLS_CLOSE_BRT = "17:00"


def _row(check: str, description: str, mask: pd.Series, s: pd.DataFrame, n_examples: int = 5) -> dict:
    cols = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
    examples = ["-".join(map(str, r)) for r in s.loc[mask, cols].head(n_examples).itertuples(index=False)]
    return {"check": check, "description": description, "tested": int(len(s)),
            "violations": int(mask.sum()), "examples": examples}


def run(s: pd.DataFrame, official: dict | None = None, all_ufs_present: bool = False) -> pd.DataFrame:
    counted = s[s["CD_TIPO_URNA"] == 1]
    home = counted[counted["SG_UF"] != "ZZ"]
    election_day = home["DT_BU_RECEBIDO_BRT"].dt.normalize().mode().iloc[0] if len(home) else None
    rows = [
        _row("I1", "presidential votes (valid + blank + null + annulled) == turnout",
             counted["total_votes"] != counted["QT_COMPARECIMENTO"], counted),
        _row("I2", "eligible == turnout + abstentions",
             counted["QT_APTOS"] != counted["QT_COMPARECIMENTO"] + counted["QT_ABSTENCOES"], counted),
        _row("I3", "turnout <= eligible", counted["QT_COMPARECIMENTO"] > counted["QT_APTOS"], counted),
        _row("I4", "section key is unique",
             counted.duplicated(["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"], keep=False), counted),
        _row("I5", "a ballot-box serial number is used by only one section (Brazil only; contingency boxes and "
             "BU recovery can explain cases, check each)",
             home.duplicated("NR_URNA_EFETIVADA", keep=False), home),
    ]
    clocks = ["DT_ABERTURA_BRT", "DT_ENCERRAMENTO_BRT", "DT_EMISSAO_BU_BRT", "DT_BU_RECEBIDO_BRT"]
    timed = home.dropna(subset=clocks)
    rows += [
        _row("I6", "clock order: opening < closing <= BU emission <= TSE reception (BRT, Brazil, complete clocks)",
             ~((timed["DT_ABERTURA_BRT"] < timed["DT_ENCERRAMENTO_BRT"])
               & (timed["DT_ENCERRAMENTO_BRT"] <= timed["DT_EMISSAO_BU_BRT"])
               & (timed["DT_EMISSAO_BU_BRT"] <= timed["DT_BU_RECEBIDO_BRT"])), timed),
        _row("I6b", "informational: sections with no opening/closing time recorded (e.g. BU recovered by "
             "contingency procedure)", home[clocks].isna().any(axis=1), home),
    ]
    if election_day is not None:
        close = election_day + pd.Timedelta(POLLS_CLOSE_BRT + ":00")
        rows.append(_row("I7", "no BU received by TSE before polls close (17:00 BRT, Brazil only)",
                         home["DT_BU_RECEBIDO_BRT"] < close, home))
    out = pd.DataFrame(rows)

    if official and all_ufs_present:
        recon = []
        for nr, expected in official.items():
            if not nr.isdigit():
                continue
            got = int(counted.get("v_" + nr, pd.Series(dtype=int)).sum())
            recon.append({"check": f"R-{nr}", "description": f"sum of section BUs for #{nr} == official total",
                          "tested": expected, "violations": got - expected, "examples": []})
        out = pd.concat([out, pd.DataFrame(recon)], ignore_index=True)
    return out
