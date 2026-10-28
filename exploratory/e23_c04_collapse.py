"""E23: sealed test C-04 (commitments/c_test_04_r2_collapse.md), candidate A collapsing or at zero in round 2.

Round-2 votes come from the section BUs fetched by e22 (`D:/tally-forensics-data/bu_r2/`), round 1 and the 2022
control from the bweb tables. Writes `reports/h8r2/c_test_04/` (`flagged_<year>.csv`, `tested_<year>.parquet`,
`missing_2026.csv`, `result.json`). Run once.

    .venv/Scripts/python exploratory/e23_c04_collapse.py          (--check: parser check on RR only, writes nothing)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data" / "interim"
LOGS = ROOT / "data" / "urna_logs" / "p3221"
BU = Path("D:/tally-forensics-data/bu_r2")
OUT = ROOT / "reports" / "h8r2" / "c_test_04"
ELECTION, A, B = 6258, 22, 13
HALF_D = {"ac", "ba", "ce", "ma", "mt", "pa", "pe", "pr", "rn", "ro", "rr", "rs", "se"}
MIN_V, COMP, ALPHA = 10, 0.05, 0.05


# --- BU parsing (DER, no schema: the structure was read from one half-D file) ---
def _tlv(b: bytes, i: int):
    t = b[i]
    i += 1
    l = b[i]
    i += 1
    if l & 0x80:
        n = l & 0x7F
        l = int.from_bytes(b[i:i + n], "big")
        i += n
    return t, i, l


def _tree(b: bytes, i: int = 0, end: int | None = None) -> list:
    end, out = len(b) if end is None else end, []
    while i < end:
        t, s, l = _tlv(b, i)
        v = b[s:s + l]
        if t & 0x20:
            out.append((t, _tree(b, s, s + l)))
        elif t == 0x04 and l > 100 and v[:1] == b"\x30":
            try:                                    # the BU is nested in an octet string; other blobs are not DER
                out.append((t, _tree(v)))
            except (IndexError, ValueError):
                out.append((t, v))
        else:
            out.append((t, int.from_bytes(v, "big", signed=True) if t in (0x02, 0x0A) or 0x80 <= t <= 0x8F else v))
        i = s + l
    return out


def _nodes(tree: list):
    for t, v in tree:
        if isinstance(v, list):
            yield t, v
            yield from _nodes(v)


def parse_bu(b: bytes) -> dict | None:
    """Election 6258 block: aptos and votes by kind (`22`, `13`, `kind2`, `kind3`)."""
    for t, kids in _nodes(_tree(b)):
        if t == 0x30 and len(kids) > 2 and kids[0] == (0x02, ELECTION) and kids[1][0] == 0x02:
            out = {"aptos_r2": kids[1][1]}
            for t2, v in _nodes(kids):
                if t2 == 0x30 and len(v) >= 2 and v[0][0] == 0x81 and v[1][0] == 0x82:
                    ident = next((x for x in v[2:] if x[0] == 0xA3), None)
                    key = str(ident[1][1][1]) if ident else f"kind{v[0][1]}"
                    out[key] = out.get(key, 0) + v[1][1]
            return out
    return None


def load_r2(ufs: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, missing = [], []
    for uf in ufs:
        status = {}
        for line in (LOGS / f"sections_{uf}.jsonl").open(encoding="utf-8"):
            s = json.loads(line)
            for lg in s.get("logs", []):
                status[lg.get("hash")] = (lg.get("status"), (lg.get("summary") or {}).get("r2", {}).get("votes"))
        man = BU / f"manifest_{uf}.jsonl"
        recs = [json.loads(x) for x in man.open(encoding="utf-8")] if man.exists() else []
        seen = set()
        for r in recs:
            key = (uf, int(r["mun"]), int(r["zone"]), int(r["section"]))
            st, log_votes = status.get(r["hash"], (None, None))
            if r["status"] != 200 or st != "Totalizado":
                missing.append({"key": key, "http": r["status"], "status": st})
                continue
            p = BU / uf / f"{r['file']}.{r['sha256'][:12]}"
            parsed = parse_bu(p.read_bytes())
            if parsed is None:
                missing.append({"key": key, "http": 200, "status": "no election block"})
                continue
            seen.add(key)
            rows.append({"uf": uf, "mun": key[1], "zone": key[2], "sec": key[3], "log_votes_r2": log_votes, **parsed})
    d = pd.DataFrame(rows).fillna(0)
    d = d.rename(columns={str(A): "F2", str(B): "L2"})
    return d.drop_duplicates(["uf", "mun", "zone", "sec"], keep=False), pd.DataFrame(missing)


def load_bweb(name: str) -> pd.DataFrame:
    d = pd.read_parquet(INTERIM / f"{name}.parquet")
    cand = [c for c in d.columns if c.startswith("v_") and c[2:].isdigit()]
    return pd.DataFrame({"uf": d["SG_UF"].str.lower(), "mun": d["CD_MUNICIPIO"].astype(int),
                         "zone": d["NR_ZONA"].astype(int), "sec": d["NR_SECAO"].astype(int),
                         "aptos": d["QT_APTOS"], "F": d[f"v_{A}"], "V": d[cand].sum(axis=1),
                         "L": d.get(f"v_{B}", 0), "blank": d["v_blank"], "null": d["v_null"]})


def detect(r1: pd.DataFrame, r2: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    k = ["uf", "mun", "zone", "sec"]
    j = r1.rename(columns={"F": "F1", "V": "V1", "aptos": "aptos_r1"})[k + ["F1", "V1", "aptos_r1"]].merge(
        r2, on=k, how="inner")
    info = {"r1_sections": len(r1), "r2_sections": len(r2), "joined": len(j)}
    j["n2"] = j["F2"] + j["L2"]
    j["composition_changed"] = (j["aptos_r2"] - j["aptos_r1"]).abs() > COMP * j["aptos_r1"].clip(lower=1)
    j["half"] = np.where(j["uf"].isin(HALF_D), "D", "C")
    t = j[(j["V1"] >= MIN_V) & (j["n2"] >= MIN_V)].copy()
    t["s1"], t["s2"] = t["F1"] / t["V1"], t["F2"] / t["n2"]
    t["m"] = (t["s2"] - t["s1"]).groupby([t["uf"], t["mun"]]).transform("median")
    p = (t["s1"] + t["m"]).clip(0.005, 0.995)
    t["p_exp"] = p
    z = (t["F2"] - t["n2"] * p) / np.sqrt(t["n2"] * p * (1 - p))
    phi = max(1.0, (1.4826 * np.median(np.abs(z - np.median(z)))) ** 2)
    t["z"], t["p_od"] = z, stats.norm.cdf(z / np.sqrt(phi))
    t["p_bin"] = stats.binom.cdf(t["F2"], t["n2"], p)
    n = len(t)
    order = np.argsort(t["p_od"].to_numpy())
    q = t["p_od"].to_numpy()[order] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    t["q_bh"] = np.empty(n)
    t.iloc[order, t.columns.get_loc("q_bh")] = np.minimum(q, 1)
    t["R0"] = (t["F1"] >= MIN_V) & (t["F2"] == 0)
    t["R1"] = t["p_od"] < ALPHA / n
    t["R1s"] = t["q_bh"] < ALPHA
    t["R2"] = (t["s1"] >= 0.70) & (t["s2"] <= t["s1"] - 0.20) & (t["V1"] >= 50)
    r0_all = j[(j["F1"] >= MIN_V) & (j["F2"] == 0)]
    info.update(tested=n, phi=phi, R0_all=len(r0_all), **{f: int(t[f].sum()) for f in ("R0", "R1", "R1s", "R2")},
                R1_composition_changed=int((t["R1"] & t["composition_changed"]).sum()))
    return t, info


def main() -> None:
    check = sys.argv[1:2] == ["--check"]
    ufs = ["rr"] if check else sorted(p.stem.split("_")[1] for p in LOGS.glob("sections_*.jsonl"))
    r2_26, missing = load_r2(ufs)
    if check:
        print(r2_26.head().to_string(), "\nmissing", len(missing))
        print("columns", list(r2_26.columns), "sections", len(r2_26))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"official_share_A_2026": 48.2148,
           "bu_share_A_2026": round(100 * r2_26["F2"].sum() / (r2_26["F2"].sum() + r2_26["L2"].sum()), 4),
           "bu_votes": {"F2": int(r2_26["F2"].sum()), "L2": int(r2_26["L2"].sum())},
           "missing_2026": len(missing)}
    missing.to_csv(OUT / "missing_2026.csv", index=False)
    b22 = load_bweb("sections_2022_t2").rename(columns={"F": "F2", "L": "L2", "aptos": "aptos_r2"})
    out = {}
    for year, r1, r2 in ((2026, load_bweb("sections_2026_t1"), r2_26),
                         (2022, load_bweb("sections_2022_t1"), b22[["uf", "mun", "zone", "sec", "F2", "L2",
                                                                     "aptos_r2"]])):
        t, info = detect(r1, r2)
        t.to_parquet(OUT / f"tested_{year}.parquet")
        t[t[["R0", "R1", "R1s", "R2"]].any(axis=1)].sort_values("p_od").to_csv(OUT / f"flagged_{year}.csv",
                                                                               index=False)
        out[year], res[str(year)] = t, info
    res["coverage_2026"] = round(res["2026"]["joined"] / res["2026"]["r1_sections"], 4)
    tests = {}
    for f in ("R0", "R1"):
        a, n_a = int(out[2026][f].sum()), len(out[2026])
        c, n_c = int(out[2022][f].sum()), len(out[2022])
        tests[f] = {"2026": [a, n_a], "2022": [c, n_c],
                    "p": float(stats.fisher_exact([[a, n_a - a], [c, n_c - c]], alternative="greater")[1])}
    ps = sorted(tests, key=lambda f: tests[f]["p"])
    run = 0.0
    for rank, f in enumerate(ps):
        run = max(run, (len(ps) - rank) * tests[f]["p"])
        tests[f]["p_holm"] = min(run, 1.0)
    res["tests"] = tests
    excess = any(tests[f]["p_holm"] < ALPHA for f in tests)
    res["decision"] = "unexplained pattern" if excess else "no signature found so far"
    if res["coverage_2026"] < 0.95:
        res["decision"] += " (partial: coverage below 95%)"
    (OUT / "result.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
