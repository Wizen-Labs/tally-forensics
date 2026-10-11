"""Runs the pre-registered analysis on a built sections table and writes a report folder."""

import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import INTERIM_DIR, REPORTS_DIR, __version__  # noqa: E402
from . import geo, integrity, residuals, temporal  # noqa: E402
from .config import analysis, ufs  # noqa: E402
from .load import add_shares  # noqa: E402


def _shift(hhmm: str, minutes: int) -> str:
    t = datetime.strptime(hhmm, "%H:%M") + pd.Timedelta(minutes=minutes)
    return t.strftime("%H:%M")


def prepare(sections: pd.DataFrame, year: int) -> pd.DataFrame:
    cfg = analysis()
    cand = cfg["candidates"][str(year)]
    s = add_shares(sections, cand["A"]["nr"], cand["B"]["nr"])
    s = residuals.add_all(s, cfg["min_valid_votes_per_section"])
    return residuals.add_covariates(s, temporal.election_day(s))


def run_window_tests(s: pd.DataFrame, cfg: dict) -> list[dict]:
    day = temporal.election_day(s)
    fw = cfg["freeze_window_brt"]
    d = fw["sensitivity_minutes"]
    windows = [("primary: freeze window", fw["start"], fw["end"]),
               (f"sensitivity: start -{d} min", _shift(fw["start"], -d), fw["end"]),
               (f"sensitivity: start +{d} min", _shift(fw["start"], d), fw["end"]),
               (f"sensitivity: end +{d} min", fw["start"], _shift(fw["end"], d))]
    windows += [(f"placebo {w['start']}-{w['end']}", w["start"], w["end"]) for w in cfg["placebo_windows_brt"]]
    home = s[s["SG_UF"] != "ZZ"]
    out = []
    for label, a, b in windows:
        start, end = temporal.window_bounds(day, a, b)
        for metric, adjust in [("margin_resid", True), ("a_resid", True), ("turnout_resid", True),
                               ("margin_resid", False)]:
            r = temporal.window_test(home, start, end, metric, cfg["permutations"], cfg["random_seed"], adjust)
            out.append({"window": label, "role": label.split(":")[0].split(" ")[0], **r})
    return out


def _plot_arrival(curve: pd.DataFrame, window: tuple, names: tuple, path: Path) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [1, 1.4]})
    ax1.bar(curve.index, curve["sections"], width=pd.Timedelta(minutes=8), color="#6b7a8f")
    ax1.set_ylabel("sections received\nper bin")
    ax2.plot(curve.index, curve["cum_share_a"], label=f"{names[0]} (cumulative)", color="#1f4e9c")
    ax2.plot(curve.index, curve["cum_share_b"], label=f"{names[1]} (cumulative)", color="#c0392b")
    ax2.set_ylabel("% of valid votes,\nin arrival order")
    for ax in (ax1, ax2):
        ax.axvspan(window[0], window[1], color="#f1c40f", alpha=0.25, lw=0)
    ax2.legend(loc="best", frameon=False)
    ax2.set_xlabel("TSE reception time (BRT); shaded = clock window of the 2026 publication freeze")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _plot_heatmap(grid: pd.DataFrame, window: tuple, bin_minutes: int, path: Path) -> None:
    m = grid["mean"].unstack("bin").sort_index(axis=1) * 100
    m = m.reindex(columns=pd.date_range(m.columns.min(), m.columns.max(), freq=f"{bin_minutes}min"))
    lim = np.nanpercentile(np.abs(m.to_numpy()), 98) if np.isfinite(m.to_numpy()).any() else 1
    fig, ax = plt.subplots(figsize=(13, 0.32 * len(m) + 2))
    im = ax.imshow(m.to_numpy(), aspect="auto", cmap="RdBu_r", vmin=-lim, vmax=lim, interpolation="nearest")
    ax.set_yticks(range(len(m)), m.index)
    ticks = list(range(0, m.shape[1], 3))
    ax.set_xticks(ticks, [m.columns[i].strftime("%H:%M") for i in ticks], rotation=90)
    cols = list(m.columns)
    inside = [i for i, c in enumerate(cols) if window[0] <= c < window[1]]
    if inside:
        ax.axvspan(inside[0] - 0.5, inside[-1] + 0.5, fill=False, ec="black", lw=1.5)
    fig.colorbar(im, ax=ax, label="mean within-location margin residual (pp)")
    ax.set_title("Geography x reception time: do sections disagree with their own polling-location siblings?")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _plot_fingerprint(s: pd.DataFrame, name_a: str, path: Path) -> None:
    d = s[["turnout", "share_a"]].dropna()
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    h = ax.hist2d(d["turnout"] * 100, d["share_a"] * 100, bins=[100, 100], range=[[40, 100], [0, 100]],
                  cmap="viridis", cmin=1)
    fig.colorbar(h[3], ax=ax, label="sections")
    ax.set_xlabel("turnout (%)")
    ax.set_ylabel(f"{name_a} share of valid votes (%)")
    ax.set_title("Election fingerprint (Klimek et al. 2012)")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def _plot_null(test: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 3.5))
    sd = test.get("null_sd") or 0
    xs = np.linspace(-4 * sd, 4 * sd, 200) if sd else np.array([0])
    if sd:
        ax.plot(xs * 100, np.exp(-0.5 * (xs / sd) ** 2), color="#6b7a8f", label="permutation null (normal approx.)")
    ax.axvline(test["effect"] * 100, color="#c0392b", lw=2, label=f"observed, p = {test['p_value']:.3g}")
    ax.set_xlabel("in-window minus out-of-window margin residual (pp)")
    ax.set_yticks([])
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def run(year: int, turn: int, log=print) -> Path:
    cfg = analysis()
    src = INTERIM_DIR / f"sections_{year}_t{turn}.parquet"
    s = prepare(pd.read_parquet(src), year)
    cand = cfg["candidates"][str(year)]
    names = (cand["A"]["name"], cand["B"]["name"])

    out = REPORTS_DIR / f"{year}_t{turn}_{datetime.now():%Y%m%d-%H%M%S}"
    out.mkdir(parents=True)
    present = sorted(s["SG_UF"].unique())
    all_present = set(ufs()) <= set(present)

    log("[check] integrity")
    checks = integrity.run(s, cfg["official_totals"].get(f"{year}-{turn}"), all_present)
    checks.to_csv(out / "integrity.csv", index=False)

    counted = s[(s["CD_TIPO_URNA"] == 1)]
    log("[test]  window permutation tests")
    tests = run_window_tests(counted, cfg)
    pd.DataFrame(tests).to_csv(out / "window_tests.csv", index=False)

    day = temporal.election_day(counted)
    window = temporal.window_bounds(day, cfg["freeze_window_brt"]["start"], cfg["freeze_window_brt"]["end"])
    home = counted[counted["SG_UF"] != "ZZ"]
    bin_m = cfg["time_bin_minutes"]

    log("[plot]  arrival curve, heatmap, fingerprint")
    curve = temporal.arrival_curve(home, bin_m)
    curve.to_csv(out / "arrival_curve.csv")
    # Plots show election evening only (17:00 to 01:00 BRT); stragglers stay in the CSVs and in every test.
    evening = (day + pd.Timedelta(hours=17), day + pd.Timedelta(hours=25))
    _plot_arrival(curve[curve.index < evening[1]], window, names, out / "arrival_curve.png")
    grid = temporal.residuals_by_bin(home, bin_m, "margin_resid", by="SG_UF")
    grid.to_csv(out / "heatmap_uf_by_time.csv")
    bins = grid.index.get_level_values("bin")
    _plot_heatmap(grid[bins < evening[1]], window, bin_m, out / "heatmap_uf_by_time.png")
    _plot_fingerprint(home, names[0], out / "fingerprint.png")
    primary = next(t for t in tests if t["window"].startswith("primary") and t["metric"] == "margin_resid_adj")
    if primary.get("effect") is not None:
        _plot_null(primary, out / "primary_test_null.png")

    by_uf = geo.summarise(home, ["SG_UF"])
    by_uf.to_csv(out / "by_uf.csv")
    by_mun = geo.summarise(home, ["SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO"])
    by_mun.to_csv(out / "by_municipality.csv")

    summary = {
        "tool_version": __version__, "year": year, "turn": turn, "generated": datetime.now().isoformat(timespec="seconds"),
        "ufs_present": present, "all_ufs_present": all_present,
        "sections_total": int(len(s)), "sections_counted": int(len(counted)),
        "sections_not_counted_by_type": s.loc[s["CD_TIPO_URNA"] != 1, "CD_TIPO_URNA"].value_counts().to_dict(),
        "share_a_pct": float(100 * counted["votes_a"].sum() / counted["valid"].sum()),
        "share_b_pct": float(100 * counted["votes_b"].sum() / counted["valid"].sum()),
        "a_z_overdispersion": residuals.overdispersion(home["a_z"]),
        "integrity_violations": {r["check"]: r["violations"] for r in checks.to_dict("records")},
        "primary_test": primary,
        "alpha": cfg["alpha"],
        "last_digit": {k: geo.last_digit_test(home[c]) for k, c in [("A", "votes_a"), ("B", "votes_b")]},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (out / "summary.md").write_text(_markdown(summary, tests, checks, names), encoding="utf-8")
    log(f"[ok]    report -> {out}")
    return out


def _markdown(summary: dict, tests: list[dict], checks: pd.DataFrame, names: tuple) -> str:
    p = summary["primary_test"]
    lines = [
        f"# Tally forensics report: {summary['year']} round {summary['turn']}",
        "",
        f"**Tool** · tally v{summary['tool_version']} · generated {summary['generated']}",
        f"**Coverage** · {len(summary['ufs_present'])} UF files · {summary['sections_counted']:,} counted sections"
        + ("" if summary["all_ufs_present"] else " · **partial: not all UFs present, no national claims**"),
        "",
        "## Integrity checks (deterministic)",
        "",
        "| Check | Description | Tested | Violations |",
        "|---|---|---:|---:|",
    ]
    lines += [f"| {r.check} | {r.description} | {r.tested:,} | {r.violations:,} |" for r in checks.itertuples()]
    lines += [
        "",
        "## Window tests (within-location permutation)",
        "",
        f"Primary hypothesis H1 at alpha = {summary['alpha']}: "
        + ("not computable" if p.get("effect") is None else
           f"effect {100 * p['effect']:+.3f} pp, p = {p['p_value']:.4f} "
           f"({'REJECT null' if p['p_value'] < summary['alpha'] else 'no evidence against null'})"),
        "",
        "| Window | Metric | Locations | In | Out | Effect (pp) | p |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for t in tests:
        eff = "n/a" if t.get("effect") is None else f"{100 * t['effect']:+.3f}"
        pv = "n/a" if t.get("p_value") is None else f"{t['p_value']:.4f}"
        lines.append(f"| {t['window']} | {t['metric']} | {t['informative_locations']:,} | {t['n_in']:,} | "
                     f"{t['n_out']:,} | {eff} | {pv} |")
    lines += [
        "",
        "## Figures",
        "",
        "- `arrival_curve.png`: sections received per bin and the arrival-order tally.",
        "- `heatmap_uf_by_time.png`: mean within-location residual by UF and reception time.",
        "- `fingerprint.png`: turnout vs share (Klimek fingerprint).",
        "- `primary_test_null.png`: observed effect against the permutation null.",
        "",
        "Read METHODOLOGY.md before interpreting any number here. A small p-value is a reason to look, not a finding.",
    ]
    return "\n".join(lines) + "\n"
