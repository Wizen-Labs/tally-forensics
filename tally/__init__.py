"""tally: forensic analysis of the Brazilian presidential vote tally from public TSE ballot-box reports."""

from pathlib import Path

__version__ = "0.2.0"

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
REPORTS_DIR = ROOT / "reports"
MANIFEST = DATA_DIR / "manifest.jsonl"
