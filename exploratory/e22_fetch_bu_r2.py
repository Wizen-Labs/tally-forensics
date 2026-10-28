"""E22: fetch every round-2 section's ballot-box report (`bu.dat`) from TSE's results site, for sealed test C-04.

The section folders and hashes come from the H7r2 crawl (`data/urna_logs/p3221/sections_<uf>.jsonl`), so only the
`bu.dat` itself is requested: one GET per section, at most 30 per second (LogCrawler's throttle, which also pauses
on HTTP 429). Files go to `D:/tally-forensics-data/bu_r2/<uf>/` unchanged; `manifest_<uf>.jsonl` there records the
URL, SHA-256, size and Last-Modified of each one. Resumable: files already in the manifest are skipped. This script
only downloads; it parses nothing.

    .venv/Scripts/python exploratory/e22_fetch_bu_r2.py [uf ...]
"""
import hashlib
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tally import DATA_DIR
from tally.urna_logs import LogCrawler

SRC = DATA_DIR / "urna_logs" / "p3221"
DEST = Path("D:/tally-forensics-data/bu_r2")


def tasks(uf: str) -> list[dict]:
    out = []
    for line in (SRC / f"sections_{uf}.jsonl").open(encoding="utf-8"):
        s = json.loads(line)
        for lg in s.get("logs", []):
            if lg.get("hash") and lg.get("file"):
                name = lg["file"].replace("-log.jez", "-bu.dat")
                folder = f"dados/{uf}/{s['mun']}/{s['zone']}/{s['section']}/{lg['hash']}"
                out.append({"uf": uf, "mun": s["mun"], "zone": s["zone"], "section": s["section"],
                            "hash": lg["hash"], "file": name, "path": f"{folder}/{name}"})
    return out


def fetch_uf(c: LogCrawler, uf: str) -> dict:
    d = DEST / uf
    d.mkdir(parents=True, exist_ok=True)
    man = DEST / f"manifest_{uf}.jsonl"
    done = {json.loads(x)["path"] for x in man.open(encoding="utf-8")} if man.exists() else set()
    todo = [t for t in tasks(uf) if t["path"] not in done]
    lock, n = threading.Lock(), {"ok": 0, "err": 0}

    def one(t: dict) -> None:
        status, body, lastmod = c._get(f"{c.root}/{t['path']}")
        rec = {**t, "status": status}
        if status == 200 and body:
            rec.update(sha256=hashlib.sha256(body).hexdigest(), bytes=len(body), last_modified=lastmod)
            (d / f"{t['file']}.{rec['sha256'][:12]}").write_bytes(body)
        with lock:
            n["ok" if status == 200 else "err"] += 1
            with man.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")

    with ThreadPoolExecutor(24) as ex:
        list(ex.map(one, todo))
    return {"uf": uf, "skipped": len(done), **n}


def main() -> None:
    ufs = sys.argv[1:] or sorted(p.stem.split("_")[1] for p in SRC.glob("sections_*.jsonl"))
    c = LogCrawler(out=DEST / "_crawler", workers=24, max_rps=30.0)
    for uf in ufs:
        print(json.dumps(fetch_uf(c, uf)), flush=True)


if __name__ == "__main__":
    main()
