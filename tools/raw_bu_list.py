"""Raw per-section counts, no statistics: candidate 22 in round 1 (bweb) next to round 2 (section BU file).

Self-contained on purpose (standard library + pandas only, its own small BU reader), so that it can be read in a few
minutes and run without trusting the rest of the lab. Every row can be checked by hand on TSE's results site.

    .venv\\Scripts\\python tools\\raw_bu_list.py --min-r1 10 --max-r2 0          (round 1 >= 10, round 2 = 0)
    .venv\\Scripts\\python tools\\raw_bu_list.py --min-r1 100 --max-r2 20 --out lista.csv
"""
import argparse
import json
from pathlib import Path

import pandas as pd

BU = Path("D:/tally-forensics-data/bu_r2")
R1 = Path(__file__).resolve().parents[1] / "data" / "interim" / "sections_2026_t1.parquet"


def der(b, i=0, end=None):
    """Minimal DER reader: list of (tag, children or value)."""
    end, out = len(b) if end is None else end, []
    while i < end:
        t, ln = b[i], b[i + 1]
        i += 2
        if ln & 0x80:
            n = ln & 0x7F
            ln, i = int.from_bytes(b[i:i + n], "big"), i + n
        v = b[i:i + ln]
        if t & 0x20:
            out.append((t, der(b, i, i + ln)))
        elif t == 0x04 and ln > 100 and v[:1] == b"\x30":
            try:
                out.append((t, der(v)))
            except IndexError:
                out.append((t, v))
        else:
            out.append((t, int.from_bytes(v, "big", signed=True) if t == 0x02 or 0x80 <= t <= 0x8F else v))
        i += ln
    return out


def walk(tree):
    for t, v in tree:
        if isinstance(v, list):
            yield t, v
            yield from walk(v)


def votes_22_13(path: Path) -> tuple[int, int] | None:
    """Votes for 22 and 13 in election 6258 (president, round 2)."""
    for t, kids in walk(der(path.read_bytes())):
        if t == 0x30 and len(kids) > 2 and kids[0] == (0x02, 6258):
            got = {}
            for t2, v in walk(kids):
                if t2 == 0x30 and len(v) >= 3 and v[0][0] == 0x81 and v[1][0] == 0x82 and v[2][0] == 0xA3:
                    got[v[2][1][1][1]] = got.get(v[2][1][1][1], 0) + v[1][1]
            return got.get(22, 0), got.get(13, 0)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-r1", type=int, default=10, help="round-1 votes for 22 at least")
    ap.add_argument("--max-r2", type=int, default=0, help="round-2 votes for 22 at most")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    r1 = pd.read_parquet(R1, columns=["SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "NR_ZONA", "NR_SECAO", "v_22", "v_13"])
    r1 = r1[r1["v_22"] >= a.min_r1]
    r1_idx = {(u.lower(), int(m), int(z), int(s)): (nm, f, l) for u, m, nm, z, s, f, l in r1.itertuples(index=False)}
    rows = []
    for man in sorted(BU.glob("manifest_*.jsonl")):
        for line in man.open(encoding="utf-8"):
            r = json.loads(line)
            key = (r["uf"], int(r["mun"]), int(r["zone"]), int(r["section"]))
            if r["status"] != 200 or key not in r1_idx:
                continue
            v = votes_22_13(BU / r["uf"] / f"{r['file']}.{r['sha256'][:12]}")
            if v and v[0] <= a.max_r2:
                nm, f1, l1 = r1_idx[key]
                rows.append({"uf": key[0].upper(), "mun": r["mun"], "municipio": nm, "zone": r["zone"],
                             "section": r["section"], "r1_22": f1, "r1_13": l1, "r2_22": v[0], "r2_13": v[1],
                             "bu_sha256": r["sha256"],
                             "url": f"https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/{r['path']}"})
    d = pd.DataFrame(rows)
    print(f"{len(d)} sections with round-1 22 >= {a.min_r1} and round-2 22 <= {a.max_r2}")
    if len(d):
        print(d.drop(columns=["bu_sha256", "url"]).to_string(index=False))
    if a.out:
        d.to_csv(a.out, index=False)


if __name__ == "__main__":
    main()
