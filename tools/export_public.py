"""Builds the public repository tree from the private lab.

Until 2026-10-28 the public tree held phase 1 (the audit) only, and phase 2 (the live run-off projection, "phase B")
stayed in the lab, committed by hash in `commitments/`. On 2026-10-28 the author decided the reveal: phase 2 is now
exported as well.

- Copies every git-tracked file except the lab-only paths below, byte-identical. Markdown is no longer edited: the
  `<!-- phase2 -->` markers are HTML comments and stay, so that the frozen `PREREGISTRATION_ROUND2.md` keeps the
  hash committed in `commitments/round2_projection.sha256`.
- Refuses to finish if an exported text links to a GitHub account other than Wizen-Labs (no link to third-party
  repositories, in particular the one that inspired the swing model).

Usage (from the lab root): python tools/export_public.py ../tally-forensics-public
The destination's .git folder, if any, is preserved; everything else in it is replaced.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent
LAB_ONLY = ["CLAUDE.md"]                              # the lab's session memory
FOREIGN_LINK = re.compile(r"github\.com/(?!Wizen-Labs\b)[A-Za-z0-9_-]+", re.I)
TEXT_EXT = {".md", ".py", ".json", ".jsonl", ".txt", ".csv", ".log", ".toml", ".cfg", ".gitignore", ".ipynb", ""}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=LAB, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p]


def main(dest: str) -> None:
    dst = Path(dest).resolve()
    dst.mkdir(parents=True, exist_ok=True)
    for child in dst.iterdir():                       # wipe everything except .git
        if child.name == ".git":
            continue
        shutil.rmtree(child) if child.is_dir() else child.unlink()

    exported, skipped, leaks = 0, [], []
    for rel in tracked_files():
        if rel in LAB_ONLY:
            skipped.append(rel)
            continue
        src, out = LAB / rel, dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)                        # byte-identical: frozen-file hashes stay valid
        exported += 1
        if out.suffix in TEXT_EXT or out.name.startswith("."):
            try:
                body = out.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                continue
            leaks += [(rel, m) for m in FOREIGN_LINK.findall(body)]

    print(f"exported {exported} files, skipped {len(skipped)} lab-only files -> {dst}")
    if leaks:
        for rel, link in leaks:
            print(f"  LINK: {rel}: {link!r}")
        sys.exit("export refused: link to a third-party GitHub account")
    print("link check: clean")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(LAB.parent / "tally-forensics-public"))
