"""E21: sealed test C-03 (commitments/c_test_03_s5_minutes.md), S5 lead, section minutes. Run once.

Input: a copy of `data/minutes/s5_minutes_answers_template.csv` filled with the TRE answers (yes / no / na; empty
if not answered). Writes `reports/h8r2/c_test_03_result.json`.

    .venv/Scripts/python exploratory/e21_c03_minutes.py data/minutes/s5_minutes_answers.csv
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
ROLES = ["same_president", "same_mesario1", "same_mesario2", "same_secretary1", "same_secretary2"]
OCC = ["bio_occurrence_r1", "bio_occurrence_r2"]
ALPHA, MIN_PAIRS = 0.05, 15


def norm(x):
    x = str(x).strip().lower() if pd.notna(x) else ""
    return {"yes": "yes", "sim": "yes", "no": "no", "nao": "no", "não": "no", "na": "na", "n/a": "na"}.get(x, "")


def outcomes(a: pd.DataFrame) -> pd.DataFrame:
    a = a.copy()
    for c in ROLES + OCC + ["substitution_r1", "substitution_r2"]:
        a[c] = a[c].map(norm)
    r = a[ROLES]
    a["O1"] = np.where((r == "").any(axis=1), np.nan, (r == "no").any(axis=1).astype(float))
    o = a[OCC]
    a["O2"] = np.where((o == "").any(axis=1) | (o == "na").any(axis=1), np.nan, (o == "yes").any(axis=1).astype(float))
    return a


def mcnemar_one_sided(f: np.ndarray, c: np.ndarray) -> dict:
    up, down = int(((f == 1) & (c == 0)).sum()), int(((f == 0) & (c == 1)).sum())
    p = stats.binomtest(up, up + down, 0.5, alternative="greater").pvalue if up + down else 1.0
    return {"pairs": int(len(f)), "flagged_only": up, "control_only": down, "both": int(((f == 1) & (c == 1)).sum()),
            "neither": int(((f == 0) & (c == 0)).sum()), "share_flagged": float(f.mean()) if len(f) else None,
            "share_control": float(c.mean()) if len(c) else None, "p": float(p)}


def holm(p):
    order = np.argsort(p)
    adj, run = [0.0] * len(p), 0.0
    for rank, i in enumerate(order):
        run = max(run, (len(p) - rank) * p[i])
        adj[i] = min(run, 1.0)
    return adj


def main() -> None:
    a = outcomes(pd.read_csv(sys.argv[1], dtype=str))
    a["pair"] = a["pair"].astype(int)
    res = {"sections_received": int(len(a))}
    tests = {}
    for o in ("O1", "O2"):
        w = a.pivot_table(index="pair", columns="role", values=o, aggfunc="first").dropna()
        if {"flagged", "control"} <= set(w.columns):
            tests[o] = mcnemar_one_sided(w["flagged"].to_numpy(), w["control"].to_numpy())
        else:
            tests[o] = mcnemar_one_sided(np.array([]), np.array([]))
    for o, adj in zip(tests, holm([tests[o]["p"] for o in tests])):
        tests[o]["p_holm"] = adj
    res["tests"] = tests
    res["per_role"] = {c: a.groupby("role")[c].value_counts().unstack(fill_value=0).to_dict("index")
                       for c in ROLES + OCC + ["substitution_r1", "substitution_r2"]}
    complete = max(tests["O1"]["pairs"], tests["O2"]["pairs"])
    either = a.assign(E=a[["O1", "O2"]].max(axis=1)).groupby("role")["E"].mean()
    if complete < MIN_PAIRS:
        res["decision"] = "inconclusive: fewer than 15 complete pairs"
    elif any(t["p_holm"] < ALPHA for t in tests.values() if t["pairs"] >= MIN_PAIRS):
        res["decision"] = "explanation supported"
    elif not either.get("flagged", 0) > either.get("control", 0):
        res["decision"] = "explanation not supported: flagged sections become an unexplained pattern"
    else:
        res["decision"] = "inconclusive: higher in flagged, not significant"
    res["share_O1_or_O2"] = either.to_dict()
    out = ROOT / "reports" / "h8r2" / "c_test_03_result.json"
    out.write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
