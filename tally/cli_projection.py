"""PHASE 2 (private until after the election): command-line extension loaded by tally/__main__.py when present."""

COMMANDS = ["backtest"]


def add_arguments(ap) -> None:
    ap.add_argument("--project", action="store_true", help="live: run the phase-2 projection every cycle")
    ap.add_argument("--bootstrap", type=int, default=50)
    ap.add_argument("--granularity", choices=["section", "municipal"], default="section")


def live_callback(args, collector):
    if not getattr(args, "project", False):
        return None
    from . import live_projection
    return live_projection.make_on_cycle(collector)


def handle(args) -> bool:
    if args.command != "backtest":
        return False
    from . import backtest
    if args.granularity == "municipal":
        backtest.run_municipal(args.year)
    else:
        backtest.run(args.year, args.bootstrap)
    return True
