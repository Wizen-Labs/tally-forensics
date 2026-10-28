"""E29: H6r2, the extended-hours tests (PREREGISTRATION_ROUND2_EXTENSION.md), with the frozen `tally/extension.py`.

Runs, in order: the natural placebo of the calibration (§4.1, real late closers of the 2022 run-off, which had no
extension), then H6a-H6c on 2026 with the primary definition (close >= 17:30 BRT), then the §2 sensitivity runs
(18:00 BRT; raw local clock). 10,000 permutations, seed 20261025, Bonferroni 0.01 / 7.
Not run here: the §4.2 placebo labels (200 random draws); see the hunt log.
Writes `reports/h6r2/`.

    .venv/Scripts/python exploratory/e29_h6r2.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import INTERIM_DIR, REPORTS_DIR, extension  # noqa: E402

PERM, SEED, ALPHA, N_TESTS = 10_000, 20261025, 0.01, 7
OUT = REPORTS_DIR / "h6r2"


def load(name: str) -> pd.DataFrame:
    d = pd.read_parquet(INTERIM_DIR / f"{name}.parquet")
    return d[d["SG_UF"] != "ZZ"]


def run(r1: pd.DataFrame, r2: pd.DataFrame, cutoff: str, close_col: str, label: str) -> dict:
    d = extension.section_changes(r1, r2, "22", "13", cutoff, close_col)
    tests = []
    for metric in extension.METRICS:
        tests.append(extension.within_municipality(d, metric, PERM, SEED))
    for metric in extension.METRICS:
        tests.append(extension.across_municipalities(d, metric, PERM, SEED))
    h6c = extension.turnout_outliers(d)
    pd.DataFrame(h6c.pop("flagged")).to_csv(OUT / f"h6c_flagged_{label}.csv", index=False)
    tests.append(h6c)
    for t in tests:
        t["reject_bonferroni"] = t["p_value"] is not None and t["p_value"] < ALPHA / N_TESTS
        if t.get("statistic") is not None:
            t["statistic_pp"] = round(100 * t["statistic"], 3)
    return {"label": label, "cutoff": cutoff, "close_col": close_col, "sections": len(d),
            "extended": int(d["extended"].sum()), "tests": tests}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res = []
    res.append(run(load("sections_2022_t1"), load("sections_2022_t2"), "17:30", "DT_ENCERRAMENTO_BRT",
                   "calibration_2022_natural_placebo"))
    r1, r2 = load("sections_2026_t1"), load("sections_2026_t2")
    res.append(run(r1, r2, "17:30", "DT_ENCERRAMENTO_BRT", "2026_primary"))
    res.append(run(r1, r2, "18:00", "DT_ENCERRAMENTO_BRT", "2026_sens_1800"))
    res.append(run(r1, r2, "17:30", "DT_ENCERRAMENTO", "2026_sens_local_clock"))
    (OUT / "result.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    for r in res:
        print(f"\n== {r['label']}: {r['sections']} sections, {r['extended']} extended")
        for t in r["tests"]:
            print(f"  {t['test']:<28} {t.get('metric', 'd_turnout'):<12} stat_pp={t.get('statistic_pp')} "
                  f"p={t['p_value']} reject={t['reject_bonferroni']} "
                  + (f"flagged={t['n_flagged']}/{t['n_extended']}" if "n_flagged" in t else ""))


if __name__ == "__main__":
    main()
