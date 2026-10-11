import numpy as np
import pandas as pd
import pytest

from tally import fetch, integrity, residuals, temporal
from tally.load import add_shares, read_presidential_rows, to_sections

from .synthetic import DAY, make_rows, write_zip


def _sections(tmp_path, **kw):
    z = write_zip(make_rows(**kw), tmp_path / "x.zip")
    s = add_shares(to_sections(read_presidential_rows(z)), "22", "13")
    return residuals.add_covariates(residuals.add_all(s, 30), DAY)


def _window():
    return temporal.window_bounds(DAY, "19:00", "20:08")


# --- parsing -----------------------------------------------------------------------------------------

def test_only_presidential_rows_and_one_row_per_section(tmp_path):
    s = _sections(tmp_path, n_locations=20)
    assert len(s) == 20 * 6
    assert {"v_22", "v_13", "v_70", "v_blank", "v_null"} <= set(s.columns)
    assert (s["total_votes"] == s["QT_COMPARECIMENTO"]).all()


def test_timezone_offset_is_inferred_from_opening_hour(tmp_path):
    s = _sections(tmp_path, n_locations=40, tz_offset_by_mun={"1003": 1, "1007": 2})
    off = s.groupby("CD_MUNICIPIO")["tz_offset_h"].first()
    assert off["1003"] == 1 and off["1007"] == 2 and off["1000"] == 0
    assert (s["DT_ABERTURA_BRT"].dt.hour == 8).all()
    assert (s["lag_min"] > 0).all()


def test_municipality_without_opening_times_gets_no_offset(tmp_path):
    rows = make_rows(n_locations=40)
    rows.loc[rows["CD_MUNICIPIO"] == "1005", "DT_ABERTURA"] = ""
    s = to_sections(read_presidential_rows(write_zip(rows, tmp_path / "x.zip")))
    off = s.groupby("CD_MUNICIPIO")["tz_offset_h"].first()
    assert np.isnan(off["1005"]) and off["1000"] == 0


# --- integrity ---------------------------------------------------------------------------------------

def test_clean_data_has_no_integrity_violations(tmp_path):
    checks = integrity.run(_sections(tmp_path, n_locations=30))
    assert checks["violations"].sum() == 0, checks


def test_integrity_flags_a_tampered_section(tmp_path):
    s = _sections(tmp_path, n_locations=30)
    s.loc[0, "total_votes"] += 5
    s.loc[1, "DT_BU_RECEBIDO_BRT"] = DAY + pd.Timedelta(hours=16)
    checks = integrity.run(s).set_index("check")["violations"]
    assert checks["I1"] == 1 and checks["I7"] == 1


def test_reconciliation_against_official_totals(tmp_path):
    s = _sections(tmp_path, n_locations=30)
    official = {"22": int(s["v_22"].sum()) + 1, "13": int(s["v_13"].sum())}
    checks = integrity.run(s, official, all_ufs_present=True).set_index("check")["violations"]
    assert checks["R-22"] == -1 and checks["R-13"] == 0


# --- residuals -----------------------------------------------------------------------------------------

def test_within_location_residual_is_leave_one_out(tmp_path):
    s = _sections(tmp_path, n_locations=5)
    loc = s[s["NR_LOCAL_VOTACAO"] == "0"]
    i = loc.index[0]
    sib = loc.drop(i)
    expected = loc.loc[i, "votes_a"] / loc.loc[i, "valid"] - sib["votes_a"].sum() / sib["valid"].sum()
    assert s.loc[i, "a_resid"] == pytest.approx(expected)


# --- temporal permutation test: false-alarm rate and power ------------------------------------------------

def test_permutation_keeps_each_location_composition():
    rng = np.random.default_rng(1)
    groups = np.repeat(np.arange(50), 4)
    labels = rng.random(200) < 0.3
    shuffled = temporal._within_group_permutation(groups, labels, rng)
    assert (np.bincount(groups, labels) == np.bincount(groups, shuffled)).all()


@pytest.mark.parametrize("seed", [11, 12, 13])
def test_clean_election_is_not_flagged(tmp_path, seed):
    s = _sections(tmp_path, seed=seed)
    r = temporal.window_test(s, *_window(), "margin_resid", permutations=500, seed=seed)
    assert r["p_value"] > 0.01, r


def test_injected_shift_in_window_is_detected(tmp_path):
    s = _sections(tmp_path, seed=5, shift_in_window=0.05)
    r = temporal.window_test(s, *_window(), "margin_resid", permutations=500, seed=5)
    assert r["p_value"] < 0.01 and r["effect"] > 0, r


def test_shift_outside_tested_window_is_not_attributed_to_it(tmp_path):
    s = _sections(tmp_path, seed=6, shift_in_window=0.05, window=("21:00", "22:00"))
    r = temporal.window_test(s, *_window(), "margin_resid", permutations=500, seed=6)
    assert r["effect"] < 0 or r["p_value"] > 0.01, r


LATE = ("20:08", "21:16")


def test_queue_confounder_fools_the_raw_test(tmp_path):
    """Reproduces the 2022 calibration failure: queued sections vote differently and arrive late."""
    s = _sections(tmp_path, seed=21, n_locations=800, queue_effect=0.08)
    r = temporal.window_test(s, *temporal.window_bounds(DAY, *LATE), "margin_resid", permutations=500, seed=1)
    assert r["p_value"] < 0.01, r   # a spurious signal; its sign depends on the window's queued fraction


def test_adjusted_test_absorbs_the_queue_confounder(tmp_path):
    s = _sections(tmp_path, seed=21, n_locations=800, queue_effect=0.08)
    r = temporal.window_test(s, *temporal.window_bounds(DAY, *LATE), "margin_resid", permutations=500, seed=1,
                             adjust=True)
    assert r["p_value"] > 0.01, r


def test_adjusted_test_still_detects_an_injected_shift(tmp_path):
    s = _sections(tmp_path, seed=22, n_locations=800, queue_effect=0.08, shift_in_window=0.05)
    r = temporal.window_test(s, *_window(), "margin_resid", permutations=500, seed=2, adjust=True)
    assert r["p_value"] < 0.01 and r["effect"] > 0, r


def test_heatmap_handles_states_with_different_bins(tmp_path):
    from tally.analyze import _plot_heatmap
    idx = pd.MultiIndex.from_tuples([("AA", DAY + pd.Timedelta(hours=h)) for h in (18, 19)]
                                    + [("BB", DAY + pd.Timedelta(hours=17))], names=["SG_UF", "bin"])
    grid = pd.DataFrame({"mean": [0.01, -0.01, 0.02], "count": [50, 50, 50]}, index=idx)
    _plot_heatmap(grid, _window(), 60, tmp_path / "h.png")
    assert (tmp_path / "h.png").stat().st_size > 0


# --- fetch ---------------------------------------------------------------------------------------------

def test_fetch_refuses_to_overwrite_a_mismatching_raw_file(tmp_path, monkeypatch):
    monkeypatch.setattr(fetch, "RAW_DIR", tmp_path)
    monkeypatch.setattr(fetch, "MANIFEST", tmp_path / "manifest.jsonl")
    monkeypatch.setattr(fetch, "_expected_sha512", lambda url: "0" * 128)
    dest = fetch.raw_path(2026, 1, "RR")
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"not the TSE file")
    with pytest.raises(RuntimeError, match="never overwritten"):
        fetch.fetch(2026, 1, "RR", log=lambda *_: None)
    assert dest.read_bytes() == b"not the TSE file"


def test_fetch_downloads_verifies_and_records(tmp_path, monkeypatch):
    payload = b"bweb bytes"
    monkeypatch.setattr(fetch, "RAW_DIR", tmp_path)
    monkeypatch.setattr(fetch, "MANIFEST", tmp_path / "manifest.jsonl")
    monkeypatch.setattr(fetch, "_expected_sha512", lambda url: __import__("hashlib").sha512(payload).hexdigest())
    monkeypatch.setattr(fetch, "_download", lambda url, dest: dest.write_bytes(payload))
    p = fetch.fetch(2026, 1, "RR", log=lambda *_: None)
    assert p.read_bytes() == payload
    assert (tmp_path / "manifest.jsonl").read_text().count("\n") == 1
