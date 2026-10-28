"""E27: the frozen round-2 audit (PREREGISTRATION_ROUND2.md, H1r2-H5r2) on TSE's round-2 bweb files.

Parameters come from the frozen `config/round2_forensics.json`; the tests are the frozen `tally.temporal` and
`tally.integrity` functions, called as in the 2022 calibration (exploratory/c4_round2_calibration_2022.py).
Official totals (H4r2) and municipal results (H5r2) are TSE's final result files in the election-night collector
archive. Writes `reports/round2_2026/`.

    .venv/Scripts/python exploratory/e27_round2_audit.py
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import DATA_DIR, INTERIM_DIR, REPORTS_DIR, integrity, temporal  # noqa: E402
from tally.analyze import prepare  # noqa: E402
from tally.config import load  # noqa: E402
from tally.live import load_state  # noqa: E402

ARCHIVE = DATA_DIR / "live" / "ele2026_e006258"
OUT = REPORTS_DIR / "round2_2026"


def freezes(s: pd.DataFrame, cfg: dict) -> list[dict]:
    """Periods >= freeze_min_minutes in which the national result file did not change in the archive, while the
    collector kept polling (no fetch gap over 2 min) and >= freeze_min_share_received of sections were received."""
    log = []
    for line in (ARCHIVE / "fetch_log.jsonl").open(encoding="utf-8"):
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "/br/br-c0001-e006258-u.json" in e.get("url", "") and e.get("status") in (200, 304):
            log.append((pd.Timestamp(e["t_utc"]).tz_convert("America/Sao_Paulo").tz_localize(None), e.get("sha256")))
    log = pd.DataFrame(log, columns=["t", "sha"]).sort_values("t")
    log["sha"] = log["sha"].ffill()
    day = temporal.election_day(s)
    log = log[log["t"] >= day + pd.Timedelta("16:30:00")]
    change = log[log["sha"] != log["sha"].shift()]
    rec = s.loc[s["SG_UF"] != "ZZ", "DT_BU_RECEBIDO_BRT"].dropna()
    out = []
    for a, b in zip(change["t"], list(change["t"])[1:]):
        minutes = (b - a).total_seconds() / 60
        polls = log[(log["t"] >= a) & (log["t"] <= b)]["t"]
        max_poll_gap = polls.diff().max().total_seconds() / 60 if len(polls) > 1 else minutes
        share = float(((rec >= a) & (rec < b)).mean())
        if minutes >= cfg["freeze_min_minutes"]:
            out.append({"start_brt": str(a), "end_brt": str(b), "minutes": round(minutes, 1),
                        "max_poll_gap_min": round(max_poll_gap, 1), "share_received": round(share, 4),
                        "is_freeze": bool(share >= cfg["freeze_min_share_received"] and max_poll_gap <= 2)})
    return out


def main() -> None:
    cfg = load("round2_forensics")
    assert cfg["protocol_frozen"]
    OUT.mkdir(parents=True, exist_ok=True)
    s = prepare(pd.read_parquet(INTERIM_DIR / "sections_2026_t2.parquet"), 2026)
    h = s[(s["SG_UF"] != "ZZ") & (s["CD_TIPO_URNA"] == 1)]
    res = {"sections": len(s), "sections_tested": len(h)}

    # H3r2
    res["H3r2_reception_gaps"] = temporal.reception_gaps(h, cfg["reception_gap_min_minutes"],
                                                         cfg["reception_gap_until_share"])
    # H4r2
    state = load_state(ARCHIVE)
    br = state["br"]
    official = {k: br["votes"][k] for k in (cfg["candidates"]["A"]["nr"], cfg["candidates"]["B"]["nr"])}
    checks = integrity.run(s, official, all_ufs_present=s["SG_UF"].nunique() == 28)
    checks.to_csv(OUT / "integrity.csv", index=False)
    res["H4r2_official_from_archive"] = {**official, "generated": br["generated"]}
    res["H4r2"] = checks[["check", "tested", "violations"]].to_dict("records")
    # H5r2
    mun = state["municipal"].copy()
    mun["CD_MUNICIPIO"] = mun["CD_MUNICIPIO"].astype(str)
    bu = s[s["CD_TIPO_URNA"] == 1].assign(CD_MUNICIPIO=lambda d: d["CD_MUNICIPIO"].astype(int).astype(str))
    agg = bu.groupby(["SG_UF", "CD_MUNICIPIO"])[[f"v_{official_nr}" for official_nr in official]].sum()
    j = mun.set_index(["SG_UF", "CD_MUNICIPIO"])[[f"v_{k}" for k in official]].join(agg, rsuffix="_bu", how="outer")
    diff = j[[f"v_{k}" for k in official]].fillna(-1).to_numpy() != j[[f"v_{k}_bu" for k in official]].fillna(-1).to_numpy()
    bad = j[diff.any(axis=1)]
    bad.to_csv(OUT / "h5r2_municipal_differences.csv")
    res["H5r2"] = {"municipalities_live": int(len(mun)), "municipalities_bu": int(len(agg)),
                   "joined": int(len(j)), "with_difference": int(len(bad))}
    # H2r2
    fr = freezes(s, cfg)
    res["H2r2_candidate_periods"] = fr
    tests = []
    for f in [x for x in fr if x["is_freeze"]]:
        a, b = pd.Timestamp(f["start_brt"]), pd.Timestamp(f["end_brt"])
        for lab, aa in (("primary", a), ("start -15", a - pd.Timedelta(minutes=15)),
                        ("start +15", a + pd.Timedelta(minutes=15))):
            r = temporal.window_test(h, aa, b, cfg["metric"], cfg["permutations"], cfg["random_seed"], cfg["adjusted"])
            tests.append({"freeze": f["start_brt"], "variant": lab, **r})
    n_fr = sum(x["is_freeze"] for x in fr)
    for t in tests:
        t["reject_bonferroni"] = t["p_value"] is not None and t["variant"] == "primary" and \
            t["p_value"] < cfg["alpha"] / max(n_fr, 1)
    res["H2r2"] = tests
    # H1r2
    scan = temporal.scan_bins(h, cfg["bin_minutes"], cfg["scan_until_share_received"], cfg["metric"],
                              cfg["permutations"], cfg["random_seed"], adjust=cfg["adjusted"])
    k = len(scan)
    scan["reject_bonferroni"] = scan["p_value"] < cfg["alpha"] / k
    scan["reject_nominal"] = scan["p_value"] < cfg["alpha"]
    scan.to_csv(OUT / "h1r2_bin_scan.csv", index=False)
    res["H1r2"] = {"bins": k, "bonferroni_threshold": cfg["alpha"] / k,
                   "reject_bonferroni": int(scan["reject_bonferroni"].sum()),
                   "reject_nominal": int(scan["reject_nominal"].sum()), "min_p": float(scan["p_value"].min())}
    (OUT / "result.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    print(scan[["start_brt", "informative_locations", "n_in", "effect", "p_value"]].assign(
        effect=lambda d: (100 * d["effect"]).round(3)).to_string(index=False))


if __name__ == "__main__":
    main()
