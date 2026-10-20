"""Parses a TSE bweb zip into one row per section for the presidential race.

Clock conventions (verified on RR 2026, see METHODOLOGY.md Â§2.3):
- DT_ABERTURA, DT_ENCERRAMENTO and DT_EMISSAO_BU are the ballot box's local clock;
- DT_BU_RECEBIDO is the TSE reception time in Brasilia time (BRT).
Polls open at 08:00 BRT nationwide, so each municipality's offset from BRT is inferred from the modal
opening hour of its ballot boxes. Abroad (UF "ZZ") polls open at 08:00 local time, so the offset cannot
be inferred and urna-side times are left unconverted (offset NaN).
"""

import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from . import INTERIM_DIR

KEYS = ["SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "NR_LOCAL_VOTACAO"]
SECTION_COLS = [
    "QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES", "CD_TIPO_URNA", "DS_SECOES_AGREGADAS",
    "NR_URNA_EFETIVADA", "DT_ABERTURA", "DT_ENCERRAMENTO", "DT_EMISSAO_BU", "DT_BU_RECEBIDO",
    "NR_JUNTA_APURADORA", "NR_TURMA_APURADORA", "DT_PLEITO",
]
USECOLS = KEYS + SECTION_COLS + ["CD_CARGO_PERGUNTA", "NR_VOTAVEL", "QT_VOTOS"]
TIME_COLS = ["DT_ABERTURA", "DT_ENCERRAMENTO", "DT_EMISSAO_BU", "DT_BU_RECEBIDO"]
SPECIAL = {"95": "v_blank", "96": "v_null", "97": "v_annulled"}
POLLS_OPEN_BRT_HOUR = 8
PARSER_VERSION = 1   # bump on any change to parsing; it invalidates the per-file cache


def _csv_member(zf: zipfile.ZipFile) -> str:
    names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if len(names) != 1:
        raise ValueError(f"expected one CSV in the zip, found {names}")
    return names[0]


# Column names that changed between election years -> current (2026) name.
RENAMES = {"DS_AGREGADAS": "DS_SECOES_AGREGADAS"}


def read_presidential_rows(zip_path: Path, office_code: str = "1", chunksize: int = 1_000_000) -> pd.DataFrame:
    """Streams the CSV and keeps only rows for the given office (1 = President)."""
    wanted = set(USECOLS) | set(RENAMES)
    parts = []
    with zipfile.ZipFile(zip_path) as zf, zf.open(_csv_member(zf)) as fh:
        for chunk in pd.read_csv(fh, sep=";", encoding="latin-1", dtype=str, usecols=lambda c: c in wanted,
                                 chunksize=chunksize, keep_default_na=False):
            parts.append(chunk[chunk["CD_CARGO_PERGUNTA"] == office_code])
    rows = pd.concat(parts, ignore_index=True).rename(columns=RENAMES)
    missing = set(USECOLS) - set(rows.columns)
    if missing:
        raise ValueError(f"{zip_path.name}: missing columns {sorted(missing)}")
    return rows[USECOLS]


def _parse_times(col: pd.Series) -> pd.Series:
    """2026 files use ISO timestamps, 2022 files use dd/mm/yyyy."""
    iso = pd.to_datetime(col, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    br = pd.to_datetime(col, format="%d/%m/%Y %H:%M:%S", errors="coerce")
    return iso.fillna(br)


def infer_offsets(sections: pd.DataFrame) -> pd.Series:
    """Hours to add to urna-local clocks to get BRT, per (UF, municipality)."""
    hour = sections["DT_ABERTURA"].dt.hour
    modal = hour.groupby([sections["SG_UF"], sections["CD_MUNICIPIO"]]).agg(
        lambda s: s.mode().iloc[0] if s.notna().any() else np.nan)
    # Boxes open at 08:00:xx BRT, i.e. modal hour 8 in BRT municipalities and 7 in UTC-4 ones.
    offset = (POLLS_OPEN_BRT_HOUR - modal).astype(float)
    offset[offset.index.get_level_values(0) == "ZZ"] = np.nan
    return offset.rename("tz_offset_h")


def to_sections(rows: pd.DataFrame) -> pd.DataFrame:
    """Pivots vote rows into one row per section, with times normalised to BRT."""
    sec_key = ["SG_UF", "CD_MUNICIPIO", "NR_ZONA", "NR_SECAO"]
    rows = rows.assign(QT_VOTOS=pd.to_numeric(rows["QT_VOTOS"]))
    rows = rows.assign(col=rows["NR_VOTAVEL"].map(SPECIAL).fillna("v_" + rows["NR_VOTAVEL"]))
    votes = rows.pivot_table(index=sec_key, columns="col", values="QT_VOTOS", aggfunc="sum", fill_value=0)
    votes.columns.name = None

    meta = rows.drop_duplicates(sec_key).set_index(sec_key)[["NM_MUNICIPIO", "NR_LOCAL_VOTACAO"] + SECTION_COLS]
    out = meta.join(votes).reset_index()
    for c in ["QT_APTOS", "QT_COMPARECIMENTO", "QT_ABSTENCOES", "CD_TIPO_URNA"]:
        out[c] = pd.to_numeric(out[c])
    for c in TIME_COLS:
        out[c] = _parse_times(out[c])

    offsets = infer_offsets(out)
    out = out.join(offsets, on=["SG_UF", "CD_MUNICIPIO"])
    shift = pd.to_timedelta(out["tz_offset_h"], unit="h")
    for c in ["DT_ABERTURA", "DT_ENCERRAMENTO", "DT_EMISSAO_BU"]:
        out[c + "_BRT"] = out[c] + shift
    out["DT_BU_RECEBIDO_BRT"] = out["DT_BU_RECEBIDO"]
    out["lag_min"] = (out["DT_BU_RECEBIDO_BRT"] - out["DT_EMISSAO_BU_BRT"]).dt.total_seconds() / 60
    out["aggregated"] = out["DS_SECOES_AGREGADAS"].ne("#NULO#")
    return out


def add_shares(sections: pd.DataFrame, nr_a: str, nr_b: str) -> pd.DataFrame:
    """Adds candidate-A/B votes, valid votes, shares and turnout."""
    vcols = [c for c in sections.columns if c.startswith("v_") and c[2:].isdigit()]
    s = sections.copy()
    s["valid"] = s[vcols].sum(axis=1)
    s["votes_a"] = s.get("v_" + nr_a, 0)
    s["votes_b"] = s.get("v_" + nr_b, 0)
    total = s["valid"] + s[[c for c in SPECIAL.values() if c in s.columns]].sum(axis=1)
    s["total_votes"] = total
    with np.errstate(divide="ignore", invalid="ignore"):
        s["share_a"] = s["votes_a"] / s["valid"]
        s["share_b"] = s["votes_b"] / s["valid"]
        s["turnout"] = s["QT_COMPARECIMENTO"] / s["QT_APTOS"]
    return s


def build(zip_paths: list[Path], year: int, turn: int, office_code: str = "1", log=print) -> Path:
    """Parses every given zip and writes data/interim/sections_<year>_t<turn>.parquet (President, office 1) or
    sections_<year>_t<turn>_c<office>.parquet for any other office (e.g. 3 = Governor)."""
    cache = INTERIM_DIR / "per_file"
    cache.mkdir(parents=True, exist_ok=True)
    tag = "" if office_code == "1" else f"_c{office_code}"
    frames = []
    for zp in zip_paths:
        part = cache / f"{zp.stem}{tag}.p{PARSER_VERSION}.parquet"
        if part.exists() and part.stat().st_mtime > zp.stat().st_mtime:
            log(f"[cache] {zp.name}")
            frames.append(pd.read_parquet(part))
            continue
        log(f"[parse] {zp.name}")
        df = to_sections(read_presidential_rows(zp, office_code))
        df.to_parquet(part, index=False)
        frames.append(df)
    sections = pd.concat(frames, ignore_index=True)
    out = INTERIM_DIR / f"sections_{year}_t{turn}{tag}.parquet"
    sections.to_parquet(out, index=False)
    log(f"[ok]    {len(sections):,} sections -> {out.name}")
    return out
