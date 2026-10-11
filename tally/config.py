"""Loads the JSON configuration. Sources and analysis parameters are data, not code."""

import json
from functools import lru_cache

from . import CONFIG_DIR


@lru_cache(maxsize=None)
def load(name: str) -> dict:
    # utf-8-sig: Windows PowerShell 5.1 writes a BOM, and the frozen config must not be re-saved to remove it.
    with open(CONFIG_DIR / f"{name}.json", encoding="utf-8-sig") as fh:
        return json.load(fh)


def bweb_url(year: int, turn: int, uf: str) -> str:
    src = load("sources")["bweb"][str(year)][str(turn)]
    return src["url"].format(uf=uf, stamp=src["stamp"])


def ufs() -> list[str]:
    return list(load("sources")["ufs"])


def analysis() -> dict:
    return load("analysis")
