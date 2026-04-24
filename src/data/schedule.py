"""MLB Stats API client for schedule, probable pitchers, lineups, venue."""

from __future__ import annotations

from datetime import date
from typing import Optional

import requests

from ..constants import MLB_STATS_API, YANKEES_TEAM_ID


def _get(path: str, params: Optional[dict] = None) -> dict:
    r = requests.get(f"{MLB_STATS_API}{path}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def yankees_game_on(target: date) -> Optional[dict]:
    """Return the Yankees game scheduled on `target`, or None if off-day."""
    data = _get(
        "/schedule",
        {
            "sportId": 1,
            "teamId": YANKEES_TEAM_ID,
            "startDate": target.isoformat(),
            "endDate": target.isoformat(),
            "hydrate": "probablePitcher,team,venue,linescore",
        },
    )
    for d in data.get("dates", []):
        for g in d.get("games", []):
            return _flatten_game(g, d["date"])
    return None


def _flatten_game(g: dict, game_date: str) -> dict:
    away = g["teams"]["away"]
    home = g["teams"]["home"]
    venue = g.get("venue", {})
    return {
        "gamePk": g["gamePk"],
        "date": game_date,
        "status": g["status"]["detailedState"],
        "venue_id": venue.get("id"),
        "venue_name": venue.get("name"),
        "away_team_id": away["team"]["id"],
        "away_team": away["team"]["name"],
        "home_team_id": home["team"]["id"],
        "home_team": home["team"]["name"],
        "away_probable_id": (away.get("probablePitcher") or {}).get("id"),
        "away_probable": (away.get("probablePitcher") or {}).get("fullName"),
        "home_probable_id": (home.get("probablePitcher") or {}).get("id"),
        "home_probable": (home.get("probablePitcher") or {}).get("fullName"),
        "yankees_home": home["team"]["id"] == YANKEES_TEAM_ID,
    }


def venue_location(venue_id: int) -> Optional[dict]:
    data = _get(f"/venues/{venue_id}", {"hydrate": "location"})
    venues = data.get("venues", [])
    if not venues:
        return None
    loc = venues[0].get("location", {}) or {}
    coords = loc.get("defaultCoordinates") or {}
    return {
        "lat": coords.get("latitude"),
        "lon": coords.get("longitude"),
        "city": loc.get("city"),
        "state": loc.get("state"),
    }


def projected_lineup(game_pk: int, team_id: int) -> list[dict]:
    """Return batting order for `team_id` from the boxscore.

    Pre-game this may be empty until lineups are posted. Falls back to the
    team's most recent lineup if unavailable.
    """
    box = _get(f"/game/{game_pk}/boxscore")
    side = "home" if box["teams"]["home"]["team"]["id"] == team_id else "away"
    team = box["teams"][side]
    order_ids = team.get("battingOrder", []) or []
    players = team.get("players", {})
    lineup = []
    for slot, pid in enumerate(order_ids, start=1):
        p = players.get(f"ID{pid}") or {}
        person = p.get("person", {})
        pos = (p.get("position") or {}).get("abbreviation")
        bat_side = (p.get("batSide") or {}).get("code")
        lineup.append(
            {
                "order": slot,
                "player_id": person.get("id"),
                "name": person.get("fullName"),
                "position": pos,
                "bats": bat_side,
            }
        )
    return lineup


def last_known_lineup(team_id: int, on_or_before: date, lookback_days: int = 10) -> list[dict]:
    """Fetch the most recent posted lineup for `team_id` within the window."""
    from datetime import timedelta

    start = (on_or_before - timedelta(days=lookback_days)).isoformat()
    end = on_or_before.isoformat()
    data = _get(
        "/schedule",
        {
            "sportId": 1,
            "teamId": team_id,
            "startDate": start,
            "endDate": end,
            "hydrate": "team",
        },
    )
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            games.append((d["date"], g["gamePk"]))
    for _, pk in sorted(games, reverse=True):
        lineup = projected_lineup(pk, team_id)
        if lineup:
            return lineup
    return []
