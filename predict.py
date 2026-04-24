#!/usr/bin/env python3
"""CLI entrypoint for the Yankees game projection.

Usage:
    python predict.py                # today's game
    python predict.py --date 2026-05-01
    python predict.py --json         # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime

from src.cli.report import render
from src.orchestrator import project


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Project tonight's Yankees game.")
    p.add_argument("--date", help="Game date YYYY-MM-DD (default: today).")
    p.add_argument(
        "--current-season",
        type=int,
        default=None,
        help="Current MLB season year (default: year of --date).",
    )
    p.add_argument(
        "--prior-season",
        type=int,
        default=None,
        help="Prior MLB season year for regression (default: current - 1).",
    )
    p.add_argument("--json", action="store_true", help="Emit JSON instead of a text report.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    target = (
        datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    )
    current = args.current_season or target.year
    prior = args.prior_season or (current - 1)

    result = project(target, prior_season=prior, current_season=current)

    if args.json:
        print(json.dumps(result, default=str, indent=2))
    else:
        print(render(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
