"""E8 (H7r2 §4): round-1 validation of the round-2 box logs, every UF, before the round-2 bweb is analysed.

A box used in both rounds keeps the round-1 events (04/10/2026) in its round-2 log. For those sections the log is
compared with the round-1 bweb exactly as H7b-H7d will compare round 2: votes, close within 60 s, box number.
The "box replaced" rule of H7r2 §2 (first ready > 5 min after DT_ABERTURA and fewer votes than bweb) is applied.

    python exploratory/e8b_round1_validation_2026.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tally import DATA_DIR

SRC = DATA_DIR / "urna_logs" / "p3221"
OUT = Path(__file__).resolve().parents[1] / "reports" / "e8_urna_logs"


def log_sections() -> pd.DataFrame:
    rows = []
    for f in sorted(SRC.glob("sections_*.jsonl")):
        last = {}
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            last[(r["mun"], r["zone"], r["section"])] = r
        for (mun, zone, sec), r in last.items():
            logs = [g for g in r.get("logs", []) if "summary" in g]
            r1 = [g["summary"]["r1"] for g in logs]
            ready = [x["ready"] for x in r1 if x["ready"]]
            close = [x["close"] for x in r1 if x["close"]]
            rows.append({"SG_UF": r["uf"].upper(), "mun": int(mun), "zone": int(zone), "sec": int(sec),
                         "status": "error" if ("error" in r or not logs) else "ok", "n_logs": len(logs),
                         "votes_log": sum(x["votes"] for x in r1), "ready_log": min(ready) if ready else None,
                         "close_log": max(close) if close else None,
                         "boxes_log": sorted({int(u) for x in r1 for u in x["urn_ids"]})})
    return pd.DataFrame(rows)


def main() -> None:
    lg = log_sections()
    bw = pd.read_parquet(DATA_DIR / "interim" / "sections_2026_t1.parquet")
    bw = bw.assign(mun=bw["CD_MUNICIPIO"].astype(int), zone=bw["NR_ZONA"].astype(int), sec=bw["NR_SECAO"].astype(int))
    m = lg.merge(bw, on=["SG_UF", "mun", "zone", "sec"], how="outer", indicator=True)
    ok = m[(m["_merge"] == "both") & (m["status"] == "ok")].copy()
    same = ok[ok["votes_log"] > 0].copy()
    day = same["DT_ABERTURA"].dt.normalize()
    close_t = day + pd.to_timedelta(same["close_log"].fillna("00:00:00"))
    ready_t = day + pd.to_timedelta(same["ready_log"].fillna("00:00:00"))
    same["d_votes"] = same["votes_log"] - same["QT_COMPARECIMENTO"]
    same["d_close_s"] = (close_t - same["DT_ENCERRAMENTO"]).dt.total_seconds()
    same["box_ok"] = [int(b) in L for b, L in zip(same["NR_URNA_EFETIVADA"], same["boxes_log"])]
    same["replaced"] = ((ready_t - same["DT_ABERTURA"]).dt.total_seconds() > 300) & (same["d_votes"] < 0)
    same["votes_ok"] = same["d_votes"] == 0
    same["close_ok"] = same["d_close_s"].abs() <= 60
    same["unexplained"] = ~same["replaced"] & ~(same["votes_ok"] & same["close_ok"] & same["box_ok"])

    by = same.groupby("SG_UF").agg(sections=("sec", "size"), votes_ok=("votes_ok", "sum"), close_ok=("close_ok", "sum"),
                                   box_ok=("box_ok", "sum"), replaced=("replaced", "sum"),
                                   unexplained=("unexplained", "sum"))
    by["log_no_r1"] = ok[ok["votes_log"] == 0].groupby("SG_UF").size()
    by["log_only"] = m[m["_merge"] == "left_only"].groupby("SG_UF").size()
    by["bweb_only"] = m[m["_merge"] == "right_only"].groupby("SG_UF").size()
    by["log_error"] = m[(m["_merge"] == "both") & (m["status"] == "error")].groupby("SG_UF").size()
    by = by.fillna(0).astype(int)
    by.loc["ALL"] = by.sum()
    OUT.mkdir(parents=True, exist_ok=True)
    by.to_csv(OUT / "round1_validation_by_uf.csv")
    cols = ["SG_UF", "mun", "zone", "sec", "votes_log", "QT_COMPARECIMENTO", "d_votes", "ready_log", "DT_ABERTURA",
            "close_log", "DT_ENCERRAMENTO", "d_close_s", "NR_URNA_EFETIVADA", "boxes_log", "replaced"]
    same[same["unexplained"] | same["replaced"]][cols].to_csv(OUT / "round1_validation_cases.csv", index=False)
    rest = m[m["_merge"] != "both"][["SG_UF", "mun", "zone", "sec", "_merge", "aggregated", "status"]]
    rest.to_csv(OUT / "round1_validation_unmatched.csv", index=False)
    pd.set_option("display.width", 200)
    print(by.to_string())
    print(same.loc[same["unexplained"], cols].head(40).to_string())


if __name__ == "__main__":
    main()
