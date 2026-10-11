"""Synthetic bweb files with a known truth, so every detector can be tested for both false alarms and power."""

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from tally.load import USECOLS

DAY = pd.Timestamp("2026-10-04")


def make_rows(n_locations=400, sections_per_location=6, seed=0, shift_in_window=0.0,
              window=("19:00", "20:08"), tz_offset_by_mun=None, queue_effect=0.0) -> pd.DataFrame:
    """One presidential row per (section, votavel) plus one Governor row per section (must be filtered out).

    shift_in_window: fraction of candidate-13 votes moved to candidate 22 in sections received inside the window.
    tz_offset_by_mun: {municipality code: hours behind BRT}; urna clocks are written in local time.
    queue_effect: the innocent confounder seen in 2022. A quarter of sections have queues, close 60-180 min late
    (so their BUs arrive late) and give candidate 22 a share lower by this many proportion points.
    """
    rng = np.random.default_rng(seed)
    tz_offset_by_mun = tz_offset_by_mun or {}
    w0, w1 = DAY + pd.Timedelta(window[0] + ":00"), DAY + pd.Timedelta(window[1] + ":00")
    rows = []
    for loc in range(n_locations):
        mun = str(1000 + loc % 20)
        behind = tz_offset_by_mun.get(mun, 0)
        p_a = rng.beta(8, 8)
        p_other = 0.08
        for k in range(sections_per_location):
            sec = str(loc * 10 + k + 1)
            aptos = int(rng.integers(250, 400))
            comp = int(rng.binomial(aptos, 0.8))
            blank, null = rng.multinomial(int(rng.binomial(comp, 0.05)), [0.4, 0.6])
            valid = comp - blank - null
            queued = queue_effect > 0 and rng.random() < 0.25
            p = max(p_a - queue_effect, 0.01) if queued else p_a
            a, b, other = rng.multinomial(valid, [p * (1 - p_other), (1 - p) * (1 - p_other), p_other])
            close_delay = float(rng.uniform(60, 180)) if queued else 1.0
            closed = DAY + pd.Timedelta(hours=17) + pd.Timedelta(minutes=close_delay)
            if queued:
                received = closed + pd.Timedelta(minutes=float(rng.uniform(5, 60)))
            else:
                received = DAY + pd.Timedelta(hours=17, minutes=5) + pd.Timedelta(minutes=float(rng.uniform(0, 290)))
            if w0 <= received < w1 and shift_in_window:
                moved = int(round(b * shift_in_window))
                a, b = a + moved, b - moved
            local = pd.Timedelta(hours=-behind)
            emission = received - pd.Timedelta(minutes=float(rng.uniform(5, 60))) + local
            meta = {
                "SG_UF": "XX", "CD_MUNICIPIO": mun, "NM_MUNICIPIO": f"MUN {mun}", "NR_ZONA": "1",
                "NR_SECAO": sec, "NR_LOCAL_VOTACAO": str(loc), "QT_APTOS": aptos, "QT_COMPARECIMENTO": comp,
                "QT_ABSTENCOES": aptos - comp, "CD_TIPO_URNA": 1, "DS_SECOES_AGREGADAS": "#NULO#",
                "NR_URNA_EFETIVADA": str(2_000_000 + loc * 10 + k),
                "DT_ABERTURA": (DAY + pd.Timedelta(hours=8, seconds=1) + local).strftime("%Y-%m-%d %H:%M:%S"),
                "DT_ENCERRAMENTO": (closed + local).strftime("%Y-%m-%d %H:%M:%S"),
                "DT_EMISSAO_BU": min(max(emission, closed + pd.Timedelta(minutes=1) + local),
                                     received + local)
                .strftime("%Y-%m-%d %H:%M:%S"),
                "DT_BU_RECEBIDO": received.strftime("%Y-%m-%d %H:%M:%S"),
                "NR_JUNTA_APURADORA": "-1", "NR_TURMA_APURADORA": "-1", "DT_PLEITO": "2026-10-04 00:00:00",
            }
            for nr, q in [("22", a), ("13", b), ("70", other), ("95", blank), ("96", null)]:
                if q:
                    rows.append({**meta, "CD_CARGO_PERGUNTA": "1", "NR_VOTAVEL": nr, "QT_VOTOS": q})
            rows.append({**meta, "CD_CARGO_PERGUNTA": "3", "NR_VOTAVEL": "10", "QT_VOTOS": comp})
    return pd.DataFrame(rows)[USECOLS]


def write_zip(rows: pd.DataFrame, path: Path) -> Path:
    buf = io.StringIO()
    rows.astype(str).to_csv(buf, sep=";", index=False, quoting=1)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bweb_1t_XX_000000000000.csv", buf.getvalue().encode("latin-1"))
        zf.writestr("_leiame.pdf", b"")
    return path
