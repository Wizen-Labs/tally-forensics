"""Synthetic checks of S6' (deviation 01): no false alarm on independent boxes with a realistic time-of-day profile,
and detection of one-minute triggers at real rates."""
import numpy as np
import pandas as pd

from tally import s6prime as s6


def synth(n_boxes=3000, seed=0):
    """Independent boxes, 08:00-17:00 BRT, opening queue and lunch dip, about 270 votes each, >= 20 s apart."""
    rng = np.random.default_rng(seed)
    t = np.arange(8 * 3600, 17 * 3600)
    rate = 1 + 1.5 * np.exp(-(t - 8 * 3600) / 3600) - 0.3 * np.exp(-((t - 12.5 * 3600) / 1800) ** 2)
    rate = rate / rate.sum()
    rows = []
    for b in range(n_boxes):
        n = rng.poisson(270)
        x = np.sort(rng.choice(t, n, replace=False, p=rate))
        x = x[np.concatenate([[True], np.diff(x) >= 20])]
        rows.append(pd.DataFrame({"box": b, "t_computed": x}))
    return pd.concat(rows, ignore_index=True), pd.Series(0.0, index=range(n_boxes))


def inject(v, boxes, minute, k):
    add = [pd.DataFrame({"box": b, "t_computed": minute * 60 + np.arange(k) * 5}) for b in boxes]
    return pd.concat([v] + add, ignore_index=True)


def test_no_false_alarm():
    v, off = synth()
    r = s6.run(v, off)
    assert r["A"]["flag"].sum() == 0 and r["B1"]["flag"].sum() == 0 and r["B2"]["flag"].sum() == 0


def test_peak_trigger():
    v, off = synth(seed=1)
    r = s6.run(inject(v, range(0, 3000, 50), 14 * 60 + 7, 3), off)           # 60 boxes, 3 votes at 14:07
    assert 14 * 60 + 7 in r["A"].loc[r["A"]["flag"], "minute"].tolist()


def test_one_vote_trigger():
    v, off = synth(seed=2)
    r = s6.run(inject(v, range(0, 3000, 2), 11 * 60 + 31, 1), off)          # 1,500 boxes, 1 vote at 11:31
    assert 11 * 60 + 31 in r["B1"].loc[r["B1"]["flag"], "minute"].tolist()


def test_coincide():
    assert s6.coincide([900, 1000], [901, 1001], [1000]) == [900]
    assert s6.coincide([900], [903], []) == []
