"""E10: when and how each round-2 box was loaded, from its log (H8r2 hunt, path 3 of the integrity-test idea).

Sections drawn for TSE's integrity test get a substitute box prepared on the eve of voting (Res. 23.673 art. 62).
That box should show a load ("Modo de carga da UE") dated the day before, or a contingency load, instead of the
routine load. This script lists every load block in every raw log: date, time, mode, section loaded, MR date.
Structural fields only, like S7; no voter trail is read.

    python exploratory/e10_load_dates_2026r2.py [--dest D:/tally-forensics-data/urna_logs_full] [--procs 6]
"""
import argparse
import io
import json
import re
import sys
import zipfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tally import DATA_DIR

SRC = DATA_DIR / "urna_logs" / "p3221" / "raw"
OUT = Path(__file__).resolve().parents[1] / "reports" / "h8r2" / "load_dates.jsonl"
NAME = re.compile(r"o03221([a-z]{2})(\d{5})(\d{4})(\d{4})-log\.jez\.([0-9a-f]{12})$")


def loads(path: str) -> dict:
    """Load (SCUE) and boot (GAP) blocks of one log, deduplicated by (app, date, mode, section)."""
    m = NAME.search(path)
    with zipfile.ZipFile(path) as z:
        text = z.read(next(n for n in z.namelist() if n.endswith(".dat"))).decode("latin1")
    blocks, cur = {}, None
    r1 = r2 = 0
    for line in text.splitlines():
        f = line.split("	")
        if len(f) < 5:
            continue
        day, app, msg = f[0][:10], f[3], f[4]
        if msg.startswith("O voto do eleitor foi computado"):
            r1 += day == "04/10/2026"
            r2 += day == "25/10/2026"
            continue
        if app not in ("SCUE", "GAP"):
            continue
        if msg.startswith("Iniciando aplica"):
            cur = {"app": app, "date": day, "time": f[0][11:19], "box": f[2]}
            blocks[(app, day, len(blocks))] = cur
        if cur is None or cur["app"] != app:
            continue
        if msg.startswith("Modo de carga da UE"):
            cur["mode"] = msg.split(" - ", 1)[-1]
        elif msg.startswith(("Munic", "Zona Eleitoral", "Seção Eleitoral", "Local de Vota")) and ":" in msg:
            cur.setdefault(msg.split(":", 1)[0][:4], msg.split(":", 1)[1].strip())
        elif msg.startswith("Urna carregada com sucesso"):
            cur["loaded"] = 1
        elif msg.startswith("Urna transitada para 2"):
            cur["transit"] = 1
        elif msg.startswith("Data e hora da geração da mídia de carga"):
            cur["media_date"] = msg.split(":", 1)[1].strip()[:10]
    seen, out = set(), []
    for b in blocks.values():
        k = tuple(sorted((x, y) for x, y in b.items() if x != "time"))
        if k not in seen and len(b) > 4:
            seen.add(k)
            out.append(b)
    return {"uf": m[1], "mun": m[2], "zone": m[3], "sec": m[4], "sha12": m[5], "r1_votes": r1, "r2_votes": r2,
            "blocks": out}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", default="D:/tally-forensics-data/urna_logs_full")
    ap.add_argument("--procs", type=int, default=6)
    a = ap.parse_args()
    files = sorted({p.name: str(p) for d in (SRC, Path(a.dest)) for p in d.glob("*/o03221*-log.jez.*")}.values())
    print(f"{len(files):,} logs", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(a.procs) as ex, open(OUT, "w", encoding="utf-8") as fh:
        for i, r in enumerate(ex.map(loads, files, chunksize=200), 1):
            fh.write(json.dumps(r) + "\n")
            if i % 50000 == 0:
                print(f"{i:,}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
