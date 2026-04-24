#!/usr/bin/env python3
"""Yankees nightly matchup CLI.

    python predict.py                        # today
    python predict.py --date 2026-05-01
    python predict.py --date 2026-05-01 --json

Flow:
    get_games(date) -> schedule json
    parse_games(json) -> DataFrame (Yankees row + others discarded)
    predict(row) -> full projection dict
    main(date) -> prints report
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime

import pandas as pd
import requests

from src.cli.report import render
from src.constants import MLB_STATS_API, YANKEES_TEAM_ID
from src.orchestrator import project


def get_games(on: str) -> dict:
    r = requests.get(
        f"{MLB_STATS_API}/schedule",
        params={
            "sportId": 1,
            "date": on,
            "hydrate": "probablePitcher,team,venue",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def parse_games(schedule_json: dict) -> pd.DataFrame:
    rows = []
    for d in schedule_json.get("dates", []):
        for g in d.get("games", []):
            rows.append(
                {
                    "gamePk": g["gamePk"],
                    "date": d["date"],
                    "home_id": g["teams"]["home"]["team"]["id"],
                    "home": g["teams"]["home"]["team"]["name"],
                    "away_id": g["teams"]["away"]["team"]["id"],
                    "away": g["teams"]["away"]["team"]["name"],
                    "home_pitcher": (g["teams"]["home"].get("probablePitcher") or {}).get("fullName"),
                    "away_pitcher": (g["teams"]["away"].get("probablePitcher") or {}).get("fullName"),
                    "venue": (g.get("venue") or {}).get("name"),
                }
            )
    return pd.DataFrame(rows)


def predict(game_row: pd.Series) -> dict:
    target = datetime.strptime(game_row["date"], "%Y-%m-%d").date()
    return project(target, prior_season=target.year - 1, current_season=target.year)


def main(on: str, as_json: bool = False, demo: bool = False, detail: bool = False) -> int:
    if demo:
        from datetime import datetime as _dt

        from src.orchestrator import project

        target = _dt.strptime(on, "%Y-%m-%d").date()
        result = project(target, prior_season=target.year - 1, current_season=target.year)
        print(json.dumps(result, default=str, indent=2) if as_json else render(result, detail=detail))
        return 0

    print(f"Fetching MLB games for {on}...")
    sched = get_games(on)
    df = parse_games(sched)

    if df.empty:
        print("No games found.")
        return 0

    yankees = df[(df["home_id"] == YANKEES_TEAM_ID) | (df["away_id"] == YANKEES_TEAM_ID)]
    if yankees.empty:
        print("Yankees are off today. Other games on the slate:")
        print(df[["away", "home", "away_pitcher", "home_pitcher"]].to_string(index=False))
        return 0

    result = predict(yankees.iloc[0])
    print(json.dumps(result, default=str, indent=2) if as_json else render(result, detail=detail))
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=date.today().strftime("%Y-%m-%d"))
    p.add_argument("--json", action="store_true")
    p.add_argument(
        "--demo",
        action="store_true",
        help="Run end-to-end against a canned fixture (no network required).",
    )
    p.add_argument(
        "--detail",
        action="store_true",
        help="Show per-batter breakdown of xwOBA / wOBA / EV / wRC+ components.",
    )
    args = p.parse_args()
    if args.demo:
        from src import demo

        demo.install()
        args.date = demo.DEMO_DATE
    raise SystemExit(main(args.date, as_json=args.json, demo=args.demo, detail=args.detail))
