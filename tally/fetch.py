"""Downloads TSE ballot-box files, verifies them against TSE's SHA-512 sidecar, and records a manifest.

Rules (see CLAUDE.md, "Backup and data control"):
- raw files are write-once: an existing file is re-verified, never overwritten;
- every download is checked against the .sha512 file TSE publishes next to it;
- every file is recorded in data/manifest.jsonl (append-only).
"""

import hashlib
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from . import MANIFEST, RAW_DIR
from .config import bweb_url

CHUNK = 1 << 20


def sha512_of(path: Path) -> str:
    h = hashlib.sha512()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _download(url: str, dest: Path) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "tally-forensics/0.1"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out, CHUNK)
    tmp.replace(dest)


def _expected_sha512(url: str) -> str:
    req = urllib.request.Request(url + ".sha512", headers={"User-Agent": "tally-forensics/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("ascii").split()[0].lower()


def _record(entry: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")


def raw_path(year: int, turn: int, uf: str) -> Path:
    return RAW_DIR / str(year) / f"t{turn}" / Path(bweb_url(year, turn, uf)).name


def fetch(year: int, turn: int, uf: str, log=print) -> Path:
    """Returns the local path of a verified bweb zip, downloading it if needed."""
    url = bweb_url(year, turn, uf)
    dest = raw_path(year, turn, uf)
    dest.parent.mkdir(parents=True, exist_ok=True)
    expected = _expected_sha512(url)

    if dest.exists():
        actual = sha512_of(dest)
        if actual != expected:
            raise RuntimeError(
                f"{dest.name}: local file does not match TSE's SHA-512. Raw files are never overwritten; "
                "move it aside by hand and investigate (TSE republication or corruption)."
            )
        log(f"[ok]   {dest.name} already present and verified")
        return dest

    log(f"[get]  {url}")
    _download(url, dest)
    actual = sha512_of(dest)
    if actual != expected:
        bad = dest.with_suffix(".zip.bad")
        dest.replace(bad)
        raise RuntimeError(f"{dest.name}: SHA-512 mismatch after download; kept as {bad.name}")

    _record({
        "file": dest.relative_to(RAW_DIR).as_posix(),
        "url": url,
        "sha512": actual,
        "bytes": dest.stat().st_size,
        "verified_against": url + ".sha512",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    log(f"[ok]   {dest.name} verified ({dest.stat().st_size / 1e6:.1f} MB)")
    return dest
