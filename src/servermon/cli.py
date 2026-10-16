"""Command-line interface for servermon.

Commands:
    snapshot  take and print one metrics sample
    watch     collect samples on a timer into the history database
    check     evaluate alert thresholds; exits 1 when anything is breached
    history   print recent recorded samples

Run `servermon <command> --help` for details.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

from . import __version__, alerting, history, metrics
from . import config as cfgmod


def _load_config(args: argparse.Namespace) -> tuple[cfgmod.Config, pathlib.Path | None]:
    explicit = pathlib.Path(args.config) if getattr(args, "config", None) else None
    conf, path = cfgmod.load_or_default(explicit)
    return conf, path


def _print_sample(sample: metrics.Sample, fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(sample.as_dict(), indent=2))
        return
    load1 = "n/a" if sample.load1 is None else f"{sample.load1:.2f}"
    print(f"time     {sample.ts}")
    print(f"uptime   {format_uptime(sample.uptime_s)}")
    print(f"cpu      {sample.cpu:6.1f} %")
    print(f"ram      {sample.mem:6.1f} %")
    print(f"swap     {sample.swap:6.1f} %")
    print(f"disk(/)  {sample.disk:6.1f} %")
    print(f"load     {load1}")


def format_uptime(seconds: int) -> str:
    """Format uptime seconds as `1d 03h 25m`."""
    minutes, _ = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    return f"{hours}h {minutes:02d}m"


def cmd_snapshot(args: argparse.Namespace) -> int:
    conf, _ = _load_config(args)
    sample = metrics.collect()
    _print_sample(sample, args.format)
    if args.top:
        print()
        print("top CPU processes:")
        for pid, name, cpu, mem in metrics.top_processes(args.top):
            print(f"  {pid:>7}  {name[:20]:<20} cpu {cpu:5.1f}%  mem {mem:5.1f}%")
    return 0 if not alerting.evaluate(sample, conf.thresholds) else 1


def cmd_watch(args: argparse.Namespace) -> int:
    conf, _ = _load_config(args)
    interval = args.interval if args.interval else conf.interval
    db: pathlib.Path = pathlib.Path(args.db) if args.db else pathlib.Path(conf.history_db)
    print(f"collecting every {interval}s into {db} (Ctrl+C to stop)")
    try:
        while True:
            sample = metrics.collect()
            history.save(db, sample)
            alerts = alerting.evaluate(sample, conf.thresholds)
            state = " ALERT: " + " | ".join(alerts) if alerts else ""
            base = (
                f"[{sample.ts}] cpu {sample.cpu:5.1f}% "
                f"ram {sample.mem:5.1f}%  disk {sample.disk:5.1f}%"
            )
            print(f"{base}{state}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    conf, _ = _load_config(args)
    sample = metrics.collect()
    alerts = alerting.evaluate(sample, conf.thresholds)
    if alerts:
        for line in alerts:
            print(f"ALERT: {line}", file=sys.stderr)
        return 1
    print("OK: all metrics within thresholds")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    conf, _ = _load_config(args)
    db: pathlib.Path = pathlib.Path(args.db) if args.db else pathlib.Path(conf.history_db)
    if not db.is_file():
        print(f"No history database at {db}. Run `servermon watch` first.", file=sys.stderr)
        return 2
    rows = history.last(db, args.limit)
    if not rows:
        print("History is empty.", file=sys.stderr)
        return 2
    print(f"{'time':<20} {'cpu %':>7} {'ram %':>7} {'disk %':>7}")
    for row in rows:
        print(f"{row['ts']:<20} {row['cpu']:>7.1f} {row['mem']:>7.1f} {row['disk']:>7.1f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="servermon",
        description="Lightweight server monitoring CLI.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--config",
        help="path to TOML config (default: ~/.config/servermon/config.toml)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_snap = sub.add_parser("snapshot", help="print one metrics sample")
    p_snap.add_argument("--json", action="store_true", help="machine-readable output")
    p_snap.add_argument("--top", type=int, metavar="N", help="also show top N processes by CPU")
    p_snap.set_defaults(func=cmd_snapshot)

    p_watch = sub.add_parser("watch", help="collect history continuously")
    p_watch.add_argument("--interval", type=int, metavar="SEC", help="seconds between samples")
    p_watch.add_argument("--db", metavar="PATH", help="history database file")
    p_watch.set_defaults(func=cmd_watch)

    p_check = sub.add_parser("check", help="exit 1 if any threshold is breached (cron-friendly)")
    p_check.set_defaults(func=cmd_check)

    p_hist = sub.add_parser("history", help="print recent samples")
    p_hist.add_argument("--limit", type=int, default=10, metavar="N")
    p_hist.add_argument("--db", metavar="PATH", help="history database file")
    p_hist.set_defaults(func=cmd_history)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Map --json flag to the `format` abstraction used in _print_sample.
    if getattr(args, "json", None):
        args.format = "json"
    else:
        args.format = "text"
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
