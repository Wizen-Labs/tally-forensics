"""PHASE 2 (lab). P6: choose the run-off projection configuration on the 2022 governor run-offs, then test it on
cases never used for the choice: the 2022 presidential run-off and the 2026 round-1 cross check.

Protocol (written before running):
1. Grid of configurations (w_transfer x k_mun x min_frac_corr).
2. Selection uses ONLY the governor run-offs. Leave-one-state-out: for each state, pick the config with the lowest
   90th-percentile absolute error on the other states, and record that config's error on the held-out state. This
   estimates how well the *selection procedure* generalises.
3. Final config = the one with the lowest p90 on all governor run-offs.
4. Held-out tests: 2022 presidential run-off and 2022 r1 -> 2026 r1. They are reported; nothing is tuned on them.
5. Target: |error| <= 0.5 pp. Results are reported per checkpoint whatever they show.
Run from the repo root after exploratory/p_build_governor_runoffs_2022.py.
"""

import itertools
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tally import INTERIM_DIR, REPORTS_DIR  # noqa: E402
from tally import runoff_bench as rb  # noqa: E402

GRID = [rb.Config(name=f"w{w}_k{int(k)}_f{f}", w_transfer=w, k_mun=k, min_frac_corr=f)
        for w, k, f in itertools.product([0.0, 0.25, 0.5, 0.75, 1.0], [1000.0, 3000.0, 10000.0], [0.0, 0.5])]
PREREG = "w0.5_k3000_f0.0"          # the configuration in the current round-2 projection draft


def governor_cases() -> dict[str, pd.DataFrame]:
    r1 = pd.read_parquet(INTERIM_DIR / "sections_2022_t1_c3.parquet")
    r2 = pd.read_parquet(INTERIM_DIR / "sections_2022_t2_c3.parquet")
    runoffs = pd.read_csv(INTERIM_DIR / "governor_runoffs_2022.csv", dtype=str)
    cases = {}
    for r in runoffs.itertuples():
        a, b = r1[r1["SG_UF"] == r.SG_UF], r2[r2["SG_UF"] == r.SG_UF]
        cases[f"gov-{r.SG_UF}"] = rb.make_case(a, b, r.A, r.B)
    return cases


def held_out_cases() -> dict[str, pd.DataFrame]:
    p1 = pd.read_parquet(INTERIM_DIR / "sections_2022_t1.parquet")
    return {"pres-2022-r2": rb.make_case(p1, pd.read_parquet(INTERIM_DIR / "sections_2022_t2.parquet"), "22", "13"),
            "pres-2022r1-to-2026r1": rb.make_case(p1, pd.read_parquet(INTERIM_DIR / "sections_2026_t1.parquet"),
                                                  "22", "13")}


def main() -> None:
    out = REPORTS_DIR / "p6_runoff_benchmark"
    out.mkdir(parents=True, exist_ok=True)
    gov = governor_cases()
    print(f"governor run-offs: {', '.join(gov)}")
    errs = rb.evaluate(gov, GRID)
    errs.to_csv(out / "governor_errors.csv", index=False)

    # leave-one-state-out estimate of the selection procedure
    loso = []
    for case in gov:
        train = errs[errs["case"] != case]
        best = rb.summarise(train).index[0]
        test = errs[(errs["case"] == case) & (errs["config"] == best)]
        loso += [{"held_out": case, "chosen": best, **r} for r in test[["pct", "error"]].to_dict("records")]
    loso = pd.DataFrame(loso)
    loso.to_csv(out / "loso.csv", index=False)
    print("\nleave-one-state-out |error| by checkpoint (pp):")
    print(loso.assign(a=loso["error"].abs()).groupby("pct")["a"].agg(["mean", "max"]).round(3).to_string())

    summary = rb.summarise(errs)
    summary.to_csv(out / "governor_summary.csv")
    final = summary.index[0]
    print(f"\nall governor run-offs, top configs:\n{summary.head(8).round(3).to_string()}")
    print(f"\npre-registered draft ({PREREG}): {summary.loc[PREREG].round(3).to_dict()}")
    print(f"FINAL (lowest p90 on governors): {final}")

    held_cases = held_out_cases()
    held = rb.evaluate(held_cases, [c for c in GRID if c.name in (final, PREREG)])
    held.to_csv(out / "held_out_errors.csv", index=False)
    print("\nHELD-OUT tests (never used for selection), error in pp:")
    print(held.pivot_table(index=["case", "pct"], columns="config", values="error").round(3).to_string())

    # Publication trigger by representativeness (owner's idea): which coverage level guarantees |error| <= 0.5?
    cfg = next(c for c in GRID if c.name == final)
    cov = rb.evaluate_with_coverage(gov, cfg)
    cov.to_csv(out / "governor_coverage.csv", index=False)
    print("\nCOVERAGE vs error (governors, final config): smallest threshold such that every point at or above it has "
          "|error| <= 0.5 pp")
    for metric in ("strata_covered", "region_min"):
        ok = None
        for thr in sorted(cov[metric].unique()):
            sub = cov[cov[metric] >= thr]
            if len(sub) and (sub["error"].abs() <= 0.5).all():
                ok = thr
                break
        n_ok = int((cov[metric] >= ok).sum()) if ok is not None else 0
        print(f"  {metric}: threshold {ok} ({n_ok} of {len(cov)} checkpoints qualify)")
    hcov = rb.evaluate_with_coverage(held_cases, cfg)
    hcov.to_csv(out / "held_out_coverage.csv", index=False)
    print("\nHELD-OUT with coverage (final config):")
    print(hcov.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
