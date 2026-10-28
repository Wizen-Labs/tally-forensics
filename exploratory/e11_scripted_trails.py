"""E11: scripted voter trails modelled on TSE's integrity test, and their injection into real boxes (H8r2 hunt, path 1).

The integrity-test logs are not released (Res. 23.673 art. 66-J), so the procedure is simulated from the rule text:
  - one Judiciary or Prosecution servant types every vote (art. 67 par. 2), in random order against the roll (par. 1);
  - the paper ballots cover a random 83-95% of the electorate (art. 63), and voting stops at 17:00 (art. 69);
  - traditional mode: no voter is present, so there is no fingerprint and every enabling is manual;
    biometric mode: real volunteers enable the box, so the trail keeps real fingerprints (art. 66-A).
A fabricated vote for an absent voter has the same constraint as the traditional mode: no real fingerprint.

`scripted_box` makes a whole test-like box; `inject` adds k scripted votes into a real box's round-2 trail.
Both return tables in `tally.signatures.VOTER_COLS`, so the frozen S1-S6 run on them unchanged. The pace
parameters are not known from the rules; they are swept, and every sweep is written to the hunt log.
"""
import numpy as np
import pandas as pd

from tally.signatures import VOTER_COLS

OPEN, CLOSE = 8 * 3600, 17 * 3600


def _trail(rng: np.random.Generator, t_start: np.ndarray, bio: bool, typing_s: float, cv: float) -> pd.DataFrame:
    n = len(t_start)
    g = lambda mean: rng.gamma(1 / cv**2, mean * cv**2, n)       # gamma with the given mean and coefficient of variation
    t_id = t_start + g(typing_s * 0.3).astype(int) + 1
    attempts = rng.integers(1, 3, n) if bio else np.zeros(n, int)
    t_en = t_id + g(typing_s * 0.2).astype(int) + 1 + 4 * attempts
    t_comp = t_en + g(typing_s * 0.5).astype(int) + 2
    return pd.DataFrame({"t_start": t_start, "t_id": t_id, "t_enabled": t_en, "t_computed": t_comp,
                         "id_type": 0, "photo": 1, "attempts": attempts, "n_scores": (attempts > 0).astype(int),
                         "score_last": np.where(attempts > 0, rng.integers(20, 120, n), 0), "bio": int(bio),
                         "worker": -1 if bio else 1, "n_confirm": 1, "bad_keys": rng.poisson(0.05, n)})


def scripted_box(electorate: int, seed: int, bio: bool = False, typing_s: float = 40.0, cv: float = 0.3,
                 box: int = 0) -> pd.DataFrame:
    """A whole box voted the integrity-test way: 83-95% of the electorate typed between 08:00 and 17:00."""
    rng = np.random.default_rng(seed)
    n = int(round(electorate * rng.uniform(0.83, 0.95)))
    gap = (CLOSE - OPEN) / max(n, 1)
    starts = OPEN + np.cumsum(rng.gamma(1 / cv**2, gap * cv**2, n)).astype(int)
    starts = starts[starts < CLOSE - 120]
    v = _trail(rng, starts, bio, typing_s, cv)
    v.insert(0, "idx", np.arange(len(v)))
    v.insert(0, "box", box)
    return v[["box"] + VOTER_COLS]


def inject(real: pd.DataFrame, k: int, seed: int, mode: str = "spread", typing_s: float = 40.0, cv: float = 0.3,
           window: tuple[int, int] = (OPEN, CLOSE)) -> pd.DataFrame:
    """Adds k manual, fingerprint-free votes to one box's trail.

    mode "spread": at random times in `window`, between real voters; mode "block": back to back, starting at a
    random time in `window`; mode "end": back to back just before the box's last real vote.
    """
    rng = np.random.default_rng(seed)
    last = int(real["t_computed"].max())
    if mode == "spread":
        starts = np.sort(rng.integers(window[0], window[1], k))
    else:
        dur = k * typing_s * 1.1
        t0 = last - dur if mode == "end" else rng.integers(window[0], max(window[0] + 1, window[1] - dur))
        starts = (t0 + np.cumsum(rng.gamma(1 / cv**2, typing_s * 1.1 * cv**2, k))).astype(int)
    fake = _trail(rng, starts, False, typing_s, cv)
    fake["box"] = real["box"].iloc[0]
    out = pd.concat([real.assign(_fake=0), fake.assign(_fake=1)], ignore_index=True).sort_values("t_start")
    out["idx"] = np.arange(len(out))
    for c in real.columns.difference(out.columns):
        out[c] = real[c].iloc[0]
    return out.reset_index(drop=True)
