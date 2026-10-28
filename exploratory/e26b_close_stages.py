"""E26b: where does the time between closing and bu.dat go? Stage times from the full box log, both rounds, for the
E26 boxes (late and control). Times only; no line text is stored.

Stages: confirm (closing confirmed) -> poll-worker registration ends -> BU report generated -> first BU print ends
-> bu.dat written. Round 1 (04/10/2026) of the same box is the comparison.

    .venv/Scripts/python exploratory/e26b_close_stages.py
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "exploratory"))
from e26_late_bu_causes import find_log, SWEEP

STAGES = {"confirm": "Procedimento de encerramento confirmado", "workers_end": "encerrou ciclo de registro de mes",
          "bu_report": "Gerando relat\xf3rio [BU] [IN", "print_end": "Fim de impress\xe3o",
          "budat": "Gerando arquivo de resultado [bu.dat]"}
DAYS = {1: "04/10/2026", 2: "25/10/2026"}


def stages(lines: list[str], day: str) -> dict:
    lines = [x for x in lines if x.startswith(day)]
    out, start = {}, 0
    for k, s in STAGES.items():
        i = next((i for i in range(start, len(lines)) if s in lines[i]), None)
        out[k] = lines[i][11:19] if i is not None else None
        start = i if i is not None else start
    return out


def main() -> None:
    o = pd.read_csv(SWEEP / "late_bu_causes.csv")
    o = o[o["log_found"]]
    rows = []
    for r in o.itertuples(index=False):
        lines = zipfile.ZipFile(find_log(r.uf, r.mun, r.zone, r.sec)).read("logd.dat").decode("latin-1").splitlines()
        for rnd, day in DAYS.items():
            rows.append({"group": r.group, "cause": r.cause, "uf": r.uf, "mun": r.mun, "zone": r.zone, "sec": r.sec,
                         "rnd": rnd, **stages(lines, day)})
    d = pd.DataFrame(rows)
    sec = {k: pd.to_timedelta(d[k]).dt.total_seconds() / 60 for k in STAGES}
    keys = list(STAGES)
    for a, b in zip(keys, keys[1:]):
        d[f"{a}_to_{b}_min"] = sec[b] - sec[a]
    d["confirm_to_budat_min"] = sec["budat"] - sec["confirm"]
    d.to_csv(SWEEP / "close_stages.csv", index=False)
    cols = [c for c in d.columns if c.endswith("_min")]
    print("median minutes per stage")
    print(d.groupby(["group", "rnd"])[cols].median().round(1).to_string())
    print("\nboxes with a stage over 30 min")
    print(d.assign(**{c: d[c] > 30 for c in cols}).groupby(["group", "rnd"])[cols].sum().to_string())
    print("\nround 2, late group: hour (box clock) at which poll-worker registration ended, when it took > 30 min")
    w = d[(d["rnd"] == 2) & (d["group"] == "late") & (d["confirm_to_workers_end_min"] > 30)]
    print(w["workers_end"].str[:2].value_counts().sort_index().to_string())
    print(w["uf"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
