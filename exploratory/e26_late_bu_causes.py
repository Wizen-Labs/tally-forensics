"""E26: why was the round-2 bu.dat of some boxes written long after closing (E25)? Reads the full box log (log.jez)
between the closing confirmation and the writing of bu.dat, for every box with emission - close > 10 min and for a
random control of normal boxes (2-5 min). Counts events only; no line text is stored (logs hold poll-worker numbers).

The direct signature of the author's hypothesis (boxes altered after closing) would be a vote computed, a new
voting session, or a change of urn id between closing and bu.dat.

    .venv/Scripts/python exploratory/e26_late_bu_causes.py
"""
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FULL = Path("D:/tally-forensics-data/urna_logs_full")
SWEEP = ROOT / "reports" / "h8r2" / "sweep"
DAY = "25/10/2026"
CLOSE = "Procedimento de encerramento confirmado"
BUDAT = "Gerando arquivo de resultado [bu.dat]"
EVENTS = {"vote_computed": "voto do eleitor foi computado", "paper_alert": "Impressora sem papel",
          "printer_other": "mpressora", "power_off": "Urna desligada", "restart": "Urna ligada em",
          "voter_enabled": "Eleitor foi habilitado", "error": "\tERRO\t", "print_bu": "Imprimindo relat\xf3rio [BU]",
          "battery": "Bateria"}


def find_log(uf: str, mun: int, zone: int, sec: int) -> Path | None:
    hits = list((FULL / uf).glob(f"o03221{uf}{mun:05d}{zone:04d}{sec:04d}-log.jez.*"))
    return hits[0] if hits else None


def scan(p: Path) -> dict:
    lines = zipfile.ZipFile(p).read("logd.dat").decode("latin-1").splitlines()
    lines = [x for x in lines if x.startswith(DAY)]
    i0 = next((i for i, x in enumerate(lines) if CLOSE in x), None)
    i1 = next((i for i, x in enumerate(lines) if BUDAT in x and (i0 is None or i > i0)), None)
    out = {"has_close": i0 is not None, "has_budat": i1 is not None, "n_budat": sum(BUDAT in x for x in lines),
           "urn_ids_r2": len({x.split("\t")[2] for x in lines if x.count("\t") >= 3})}
    seg = lines[i0:i1] if i0 is not None and i1 is not None else []
    for k, s in EVENTS.items():
        out[k] = sum(s in x for x in seg)
    out["seg_urn_ids"] = len({x.split("\t")[2] for x in seg if x.count("\t") >= 3})
    out["votes_after_close"] = sum(EVENTS["vote_computed"] in x for x in lines[i0:]) if i0 is not None else None
    return out


def cause(r) -> str:
    if r["votes_after_close"] or r["voter_enabled"] or r["seg_urn_ids"] > 1:
        return "VOTING AFTER CLOSE / URN CHANGE"
    if r["paper_alert"]:
        return "printer out of paper" + (" + power cycle" if r["power_off"] else "")
    if r["power_off"]:
        return "power cycle"
    if r["printer_other"]:
        return "other printer event"
    return "unclassified"


def main() -> None:
    d = pd.read_csv(SWEEP / "bu_emission.csv")
    late = d[d["emit_minus_close_min"] > 10].assign(group="late")
    ctrl = d[d["emit_minus_close_min"].between(2, 5)].sample(3000, random_state=26).assign(group="control")
    rows = []
    for r in pd.concat([late, ctrl]).itertuples(index=False):
        p = find_log(r.uf, r.mun, r.zone, r.sec)
        base = {"group": r.group, "uf": r.uf, "mun": r.mun, "zone": r.zone, "sec": r.sec,
                "emit_minus_close_min": r.emit_minus_close_min, "log_found": p is not None}
        rows.append({**base, **(scan(p) if p else {})})
    o = pd.DataFrame(rows)
    ok = o["log_found"] & o["has_close"].fillna(False).astype(bool) & o["has_budat"].fillna(False).astype(bool)
    o["cause"] = "no full log"
    o.loc[ok, "cause"] = o[ok].apply(cause, axis=1)
    o.to_csv(SWEEP / "late_bu_causes.csv", index=False)
    print(o.groupby("group")["log_found"].agg(["size", "sum"]).to_string())
    print(pd.crosstab(o["cause"], o["group"]).to_string())
    print("votes computed after close, any box:", int(o["votes_after_close"].fillna(0).gt(0).sum()))
    late_ok = o[(o["group"] == "late") & ok]
    print(pd.crosstab(pd.cut(late_ok["emit_minus_close_min"], [10, 30, 60, 120, 1e9]), late_ok["cause"]).to_string())


if __name__ == "__main__":
    main()
