"""H8r2 second pass: fetch the full log of every section that the H7r2 crawl summarised but did not keep.

The H7r2 crawler (`tally/urna_logs.py`, frozen) keeps the raw log only for late or unusual sections and a 1% sample.
This pass reads its per-UF summaries, fetches each remaining log once from the URL it recorded, checks it against the
SHA-256 that H7r2 wrote, and stores it under `dest/<uf>/<file>.<sha[:12]>`. The H7r2 code is reused, not changed.
"""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import DATA_DIR
from .urna_logs import LogCrawler

SRC = DATA_DIR / "urna_logs" / "p3221"


def pending(uf: str, src: Path = SRC, dest: Path | None = None) -> list[dict]:
    """Logs listed in the H7r2 summary of `uf` whose raw file is in neither the H7r2 folder nor `dest`."""
    uf = uf.lower()
    seen, out = set(), []
    for line in (src / f"sections_{uf}.jsonl").read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        for g in row.get("logs", []):
            sha = g.get("sha256")
            if not sha or sha in seen:
                continue
            seen.add(sha)
            name = f"{g['file']}.{sha[:12]}"
            if (src / "raw" / uf / name).exists() or (dest and (dest / uf / name).exists()):
                continue
            out.append({"uf": uf, "mun": row["mun"], "zone": row["zone"], "section": row["section"],
                        "hash": g["hash"], "file": g["file"], "sha256": sha})
    return out


def fetch_uf(uf: str, dest: Path, src: Path = SRC, max_rps: float = 30.0, workers: int = 24, log=print) -> dict:
    """Fetches the pending logs of one UF. Resumable; a file whose SHA-256 differs from H7r2's is not stored."""
    uf = uf.lower()
    todo = pending(uf, src, dest)
    crawler = LogCrawler(out=dest / "_crawler", max_rps=max_rps, workers=workers, log=log)
    (dest / uf).mkdir(parents=True, exist_ok=True)
    log(f"{uf}: {len(todo):,} logs to fetch")

    def one(t: dict) -> dict:
        url = f"{crawler.root}/dados/{uf}/{t['mun']}/{t['zone']}/{t['section']}/{t['hash']}/{t['file']}"
        status, body, _ = crawler._get(url)
        if status != 200:
            return {**t, "result": f"HTTP {status}"}
        sha = hashlib.sha256(body).hexdigest()
        if sha != t["sha256"]:
            return {**t, "result": f"sha mismatch {sha}"}
        (dest / uf / f"{t['file']}.{sha[:12]}").write_bytes(body)
        return {**t, "result": "ok"}

    n = bad = 0
    with ThreadPoolExecutor(workers) as ex, open(dest / f"fetch_{uf}.jsonl", "a", encoding="utf-8") as fh:
        for r in ex.map(one, todo):
            fh.write(json.dumps(r) + "\n")
            n += 1
            bad += r["result"] != "ok"
            if n % 5000 == 0:
                fh.flush()
                log(f"{uf}: {n:,}/{len(todo):,} ({bad} failed)")
    log(f"{uf}: finished {n:,} logs, {bad} failed")
    return {"uf": uf, "fetched": n, "failed": bad}


def raw_path(uf: str, file: str, sha: str, dest: Path, src: Path = SRC) -> Path | None:
    """Where the raw log is, in the H7r2 folder or the second-pass folder."""
    name = f"{file}.{sha[:12]}"
    for p in (src / "raw" / uf.lower() / name, dest / uf.lower() / name):
        if p.exists():
            return p
    return None
