"""Command line: python -m tally {fetch,build,analyze,all,live} ...

Optional modules named `tally/cli_*.py` can add commands and arguments; the tool runs without them.
"""

import argparse
import importlib
import pkgutil
import sys
from pathlib import Path

from . import analyze, fetch, load
from .config import analysis, ufs

CONFIRMATORY_YEARS = {2026}
EXTENSIONS = [importlib.import_module(f"tally.{m.name}")
              for m in pkgutil.iter_modules([str(Path(__file__).parent)]) if m.name.startswith("cli_")]


def _ufs(args) -> list[str]:
    if args.all_ufs:
        return ufs()
    if not args.uf:
        sys.exit("choose --uf XX [YY ...] or --all-ufs (all 28 files are several GB)")
    return [u.upper() for u in args.uf]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="tally")
    extra = [c for ext in EXTENSIONS for c in ext.COMMANDS]
    ap.add_argument("command", choices=["fetch", "build", "analyze", "all", "live"] + extra)
    ap.add_argument("--election", default="6258", help="live: TSE election code (6257 = 2026 round 1, 6258 = round 2)")
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--until", help="live: stop at this BRT time, HH:MM")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--no-cs", action="store_true", help="live: skip the 28 section-configuration files")
    ap.add_argument("--year", type=int)
    ap.add_argument("--turn", type=int, default=1)
    ap.add_argument("--uf", nargs="*")
    ap.add_argument("--all-ufs", action="store_true")
    ap.add_argument("--exploratory", action="store_true",
                    help="allow analysing a confirmatory year before the protocol is frozen; the report is labelled")
    for ext in EXTENSIONS:
        ext.add_arguments(ap)
    args = ap.parse_args(argv)

    if args.command == "live":
        from . import live
        col = live.Collector(args.election)
        callbacks = [cb for ext in EXTENSIONS if (cb := ext.live_callback(args, col))]
        on_cycle = (lambda: [cb() for cb in callbacks]) if callbacks else None
        if args.once:
            col.cycle(with_cs=not args.no_cs)
            if on_cycle:
                on_cycle()
        else:
            col.run(args.interval, args.until, with_cs=not args.no_cs, on_cycle=on_cycle)
        return

    if any(ext.handle(args) for ext in EXTENSIONS):
        return

    if args.command in ("fetch", "build", "all"):
        paths = [fetch.fetch(args.year, args.turn, uf) for uf in _ufs(args)]
        if args.command in ("build", "all"):
            load.build(paths, args.year, args.turn, analysis()["office_code"])

    if args.command in ("analyze", "all"):
        frozen = analysis().get("protocol_frozen", False)
        if args.year in CONFIRMATORY_YEARS and not frozen and not args.exploratory:
            sys.exit(f"{args.year} is the confirmatory dataset and the protocol is not frozen yet. Review "
                     "METHODOLOGY.md, then set \"protocol_frozen\": true in config/analysis.json "
                     "(or pass --exploratory, which labels the report).")
        out = analyze.run(args.year, args.turn)
        if args.year in CONFIRMATORY_YEARS and not frozen:
            (out / "EXPLORATORY_RUN_PROTOCOL_NOT_FROZEN.txt").write_text(
                "This report was produced before the protocol was frozen. It is not confirmatory.\n")


if __name__ == "__main__":
    main()
