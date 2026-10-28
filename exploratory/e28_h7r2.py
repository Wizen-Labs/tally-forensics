"""E28: H7r2 (PREREGISTRATION_ROUND2_LOGS.md), box logs against the round-2 bweb, plus two exploratory cross-checks
against the section BU files (e22): BU emission time vs bweb DT_EMISSAO_BU, and bweb votes for 22/13 vs the BU file.

H7a coverage, H7b votes, H7c close within 60 s, H7d box number, H7e extended set (close >= 17:30 BRT). Explained
category: box replaced during voting (first ready > 5 min after DT_ABERTURA and fewer log votes than bweb).
Times are compared in local time, as the protocol fixes. Writes `reports/h7r2/`.

    .venv/Scripts/python exploratory/e28_h7r2.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "exploratory"))
from e23_c04_collapse_a1 import LOGS  # noqa: E402

INTERIM = ROOT / "data" / "interim"
SWEEP = ROOT / "reports" / "h8r2" / "sweep"
OUT = ROOT / "reports" / "h7r2"
KEY = ["uf", "mun", "zone", "sec"]


def sec(hms: str | None) -> float | None:
    if not isinstance(hms, str):
        return None
    h, m, s = map(int, hms.split(":"))
    return h * 3600 + m * 60 + s


def load_logs() -> pd.DataFrame:
    rows = []
    for jl in sorted(LOGS.glob("sections_*.jsonl")):
        for line in jl.open(encoding="utf-8"):
            s = json.loads(line)
            r2s = [(lg.get("summary") or {}).get("r2") or {} for lg in s.get("logs", [])]
            r2s = [r for r in r2s if r.get("votes") is not None or r.get("close")]
            if not s.get("logs"):
                continue
            closes = [r["close"] for r in r2s if r.get("close")]
            readies = [r["ready"] for r in r2s if r.get("ready")]
            rows.append({"uf": s["uf"].lower(), "mun": int(s["mun"]), "zone": int(s["zone"]), "sec": int(s["section"]),
                         "n_logs": len(s["logs"]), "log_votes": sum(r.get("votes") or 0 for r in r2s),
                         "log_close": max(closes) if closes else None, "log_ready": min(readies) if readies else None,
                         "log_urns": sorted({u for r in r2s for u in r.get("urn_ids") or []})})
    return pd.DataFrame(rows).drop_duplicates(KEY, keep="last")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    b = pd.read_parquet(INTERIM / "sections_2026_t2.parquet")
    b = b.assign(uf=b["SG_UF"].str.lower(), mun=b["CD_MUNICIPIO"].astype(int), zone=b["NR_ZONA"].astype(int),
                 sec=b["NR_SECAO"].astype(int))
    lg = load_logs()
    j = b.merge(lg, on=KEY, how="outer", indicator=True)
    res = {"bweb_sections": len(b), "log_sections": len(lg),
           "H7a": {"bweb_without_log": int((j["_merge"] == "left_only").sum()),
                   "log_without_bweb": int((j["_merge"] == "right_only").sum())}}
    j[j["_merge"] != "both"][KEY + ["_merge"]].to_csv(OUT / "h7a_coverage.csv", index=False)
    m = j[j["_merge"] == "both"].copy()
    open_s = m["DT_ABERTURA"].dt.hour * 3600 + m["DT_ABERTURA"].dt.minute * 60 + m["DT_ABERTURA"].dt.second
    close_s = m["DT_ENCERRAMENTO"].dt.hour * 3600 + m["DT_ENCERRAMENTO"].dt.minute * 60 + m["DT_ENCERRAMENTO"].dt.second
    m["log_close_s"], m["log_ready_s"] = m["log_close"].map(sec), m["log_ready"].map(sec)
    replaced = (m["log_ready_s"] - open_s > 300) & (m["log_votes"] < m["QT_COMPARECIMENTO"])
    m["H7b_fail"] = m["log_votes"] != m["QT_COMPARECIMENTO"]
    m["H7c_fail"] = (m["log_close_s"] - close_s).abs() > 60
    m["H7d_fail"] = ~m.apply(lambda r: str(int(r["NR_URNA_EFETIVADA"])).zfill(8) in r["log_urns"]
                             if pd.notna(r["NR_URNA_EFETIVADA"]) and str(r["NR_URNA_EFETIVADA"]).isdigit() else False,
                             axis=1)
    m["ext_bweb"] = m["DT_ENCERRAMENTO_BRT"].dt.hour * 60 + m["DT_ENCERRAMENTO_BRT"].dt.minute >= 17 * 60 + 30
    m["ext_log"] = (m["log_close_s"] / 60 + m["tz_offset_h"].fillna(0) * 60) >= 17 * 60 + 30
    m["H7e_fail"] = m["ext_bweb"] != m["ext_log"]
    m["explained_replaced"] = replaced
    for c in ("H7b", "H7c", "H7d", "H7e"):
        f = m[f"{c}_fail"]
        res[c] = {"fail": int(f.sum()), "explained_box_replaced": int((f & replaced).sum()),
                  "unexplained": int((f & ~replaced).sum())}
    cols = KEY + ["QT_COMPARECIMENTO", "log_votes", "n_logs", "DT_ABERTURA", "log_ready", "DT_ENCERRAMENTO", "log_close",
                  "NR_URNA_EFETIVADA", "log_urns", "ext_bweb", "ext_log", "explained_replaced",
                  "H7b_fail", "H7c_fail", "H7d_fail", "H7e_fail"]
    m[m[["H7b_fail", "H7c_fail", "H7d_fail", "H7e_fail"]].any(axis=1)][cols].to_csv(OUT / "h7_discrepancies.csv",
                                                                                     index=False)
    res["extended_sections"] = {"bweb": int(m["ext_bweb"].sum()), "log": int(m["ext_log"].sum())}

    # exploratory: BU file emission time vs bweb DT_EMISSAO_BU (both local time)
    e = pd.read_csv(SWEEP / "bu_emission.csv")
    e["bu_emit"] = pd.to_datetime(e["bu_emitted"], format="%Y%m%dT%H%M%S")
    x = b.merge(e[KEY + ["bu_emit"]], on=KEY, how="inner")
    dt = (x["DT_EMISSAO_BU"] - x["bu_emit"]).dt.total_seconds()
    res["X1_bu_emission_vs_bweb"] = {"joined": len(x), "equal": int((dt == 0).sum()),
                                     "within_60s": int((dt.abs() <= 60).sum()), "over_60s": int((dt.abs() > 60).sum())}
    x[dt.abs() > 60][KEY + ["DT_EMISSAO_BU", "bu_emit"]].to_csv(OUT / "x1_emission_mismatch.csv", index=False)
    # exploratory: bweb votes vs BU file votes (sections tested in C-04 and its amendment)
    t = pd.read_parquet(ROOT / "reports" / "h8r2" / "c_test_04" / "tested_2026.parquet", columns=KEY + ["F2", "L2"])
    y = b.merge(t, on=KEY, how="inner")
    bad = y[(y["v_22"] != y["F2"]) | (y["v_13"] != y["L2"])]
    res["X2_votes_bweb_vs_bu_file"] = {"joined": len(y), "differ": len(bad)}
    bad[KEY + ["v_22", "F2", "v_13", "L2"]].to_csv(OUT / "x2_vote_mismatch.csv", index=False)
    (OUT / "result.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
