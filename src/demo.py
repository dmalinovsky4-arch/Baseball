"""Offline demo fixture.

Call `install()` to monkey-patch every data-fetching function with canned
responses so `predict.py --demo` runs end-to-end without network access.
Scenario: Yankees @ Astros at Daikin Park, 2026-04-24. Framber Valdez (L)
vs Max Fried (L). Numbers are plausible (2024-25 style) but not live.
"""

from __future__ import annotations

from typing import Optional

import pandas as pd

DEMO_DATE = "2026-04-24"
DAIKIN_VENUE_ID = 2392

GAME = {
    "gamePk": 999001,
    "date": DEMO_DATE,
    "status": "Scheduled",
    "venue_id": DAIKIN_VENUE_ID,
    "venue_name": "Daikin Park",
    "away_team_id": 147,
    "away_team": "New York Yankees",
    "home_team_id": 117,
    "home_team": "Houston Astros",
    "away_probable_id": 608331,
    "away_probable": "Max Fried",
    "home_probable_id": 664285,
    "home_probable": "Framber Valdez",
    "yankees_home": False,
}

PITCHER_THROWS = {608331: "L", 664285: "L"}

NYY_LINEUP = [
    {"order": 1, "player_id": 592450, "name": "Aaron Judge",          "position": "CF", "bats": "R"},
    {"order": 2, "player_id": 519203, "name": "Giancarlo Stanton",    "position": "DH", "bats": "R"},
    {"order": 3, "player_id": 572761, "name": "Paul Goldschmidt",     "position": "1B", "bats": "R"},
    {"order": 4, "player_id": 665742, "name": "Cody Bellinger",       "position": "RF", "bats": "L"},
    {"order": 5, "player_id": 641355, "name": "Anthony Santander",    "position": "LF", "bats": "S"},
    {"order": 6, "player_id": 683011, "name": "Jazz Chisholm Jr.",    "position": "2B", "bats": "L"},
    {"order": 7, "player_id": 683002, "name": "Anthony Volpe",        "position": "SS", "bats": "R"},
    {"order": 8, "player_id": 669224, "name": "Austin Wells",         "position": "C",  "bats": "L"},
    {"order": 9, "player_id": 663837, "name": "Trent Grisham",        "position": "DH", "bats": "L"},
]

HOU_LINEUP = [
    {"order": 1, "player_id": 514888, "name": "Jose Altuve",          "position": "LF", "bats": "R"},
    {"order": 2, "player_id": 670541, "name": "Isaac Paredes",        "position": "3B", "bats": "R"},
    {"order": 3, "player_id": 670541, "name": "Yordan Alvarez",       "position": "DH", "bats": "L"},
    {"order": 4, "player_id": 572233, "name": "Christian Walker",     "position": "1B", "bats": "R"},
    {"order": 5, "player_id": 665161, "name": "Jeremy Pena",          "position": "SS", "bats": "R"},
    {"order": 6, "player_id": 673237, "name": "Yainer Diaz",          "position": "C",  "bats": "R"},
    {"order": 7, "player_id": 676801, "name": "Cam Smith",            "position": "RF", "bats": "R"},
    {"order": 8, "player_id": 643289, "name": "Mauricio Dubon",       "position": "2B", "bats": "R"},
    {"order": 9, "player_id": 676694, "name": "Jake Meyers",          "position": "CF", "bats": "R"},
]

# Make the id collision explicit (Alvarez's id placeholder). Patch:
HOU_LINEUP[2]["player_id"] = 670541 + 1  # 670542 for Alvarez to avoid dup key


def _fg_batter(name, pa, woba, wrc, avg, slg, hr):
    return {"Name": name, "PA": pa, "wOBA": woba, "wRC+": wrc, "AVG": avg, "SLG": slg, "HR": hr}


FG_BATTERS = pd.DataFrame([
    _fg_batter("Aaron Judge",        704, 0.458, 218, 0.322, 0.701, 58),
    _fg_batter("Giancarlo Stanton",  459, 0.331, 117, 0.233, 0.475, 27),
    _fg_batter("Paul Goldschmidt",   654, 0.321, 111, 0.245, 0.414, 22),
    _fg_batter("Cody Bellinger",     598, 0.330, 109, 0.266, 0.426, 18),
    _fg_batter("Anthony Santander",  665, 0.354, 129, 0.235, 0.506, 44),
    _fg_batter("Jazz Chisholm Jr.",  550, 0.323, 109, 0.250, 0.430, 24),
    _fg_batter("Anthony Volpe",      626, 0.314, 103, 0.243, 0.428, 12),
    _fg_batter("Austin Wells",       499, 0.329, 118, 0.229, 0.395, 13),
    _fg_batter("Trent Grisham",      269, 0.307, 100, 0.190, 0.385, 9),
    _fg_batter("Jose Altuve",        659, 0.338, 121, 0.295, 0.439, 20),
    _fg_batter("Isaac Paredes",      658, 0.333, 116, 0.238, 0.433, 19),
    _fg_batter("Yordan Alvarez",     412, 0.393, 160, 0.308, 0.567, 22),
    _fg_batter("Christian Walker",   550, 0.339, 119, 0.251, 0.468, 26),
    _fg_batter("Jeremy Pena",        574, 0.307, 102, 0.266, 0.423, 15),
    _fg_batter("Yainer Diaz",        510, 0.319, 112, 0.294, 0.429, 16),
    _fg_batter("Cam Smith",          300, 0.310, 105, 0.260, 0.420, 10),
    _fg_batter("Mauricio Dubon",     480, 0.300, 93,  0.259, 0.383, 8),
    _fg_batter("Jake Meyers",        380, 0.297, 90,  0.248, 0.368, 7),
])
FG_BATTERS["HR_per_PA"] = FG_BATTERS["HR"] / FG_BATTERS["PA"]


def _fg_pitcher(name, tbf, woba, fip_minus):
    return {"Name": name, "TBF": tbf, "wOBA": woba, "FIP-": fip_minus}


FG_PITCHERS = pd.DataFrame([
    _fg_pitcher("Max Fried",          732, 0.283, 84),
    _fg_pitcher("Framber Valdez",     786, 0.296, 94),
])


# Statcast aggregates — include overall, vs_L, vs_R splits.
def _sc_batter_row(pid, pa, xwoba, ev, pa_l, x_l, ev_l, pa_r, x_r, ev_r):
    return {
        "batter": pid,
        "PA": pa, "xwOBA": xwoba, "EV50": ev, "BBE": int(pa * 0.7),
        "PA_vs_L": pa_l, "xwOBA_vs_L": x_l, "EV50_vs_L": ev_l, "BBE_vs_L": int(pa_l * 0.7),
        "PA_vs_R": pa_r, "xwOBA_vs_R": x_r, "EV50_vs_R": ev_r, "BBE_vs_R": int(pa_r * 0.7),
    }


SC_BATTERS = pd.DataFrame([
    _sc_batter_row(592450, 700, 0.448, 97.9,  190, 0.460, 98.3, 510, 0.444, 97.7),
    _sc_batter_row(519203, 450, 0.330, 94.6,  130, 0.345, 95.0, 320, 0.324, 94.4),
    _sc_batter_row(572761, 650, 0.315, 90.8,  180, 0.325, 91.0, 470, 0.311, 90.7),
    _sc_batter_row(665742, 595, 0.335, 91.4,  150, 0.300, 90.2, 445, 0.347, 91.8),
    _sc_batter_row(641355, 660, 0.345, 92.5,  190, 0.330, 92.0, 470, 0.351, 92.7),
    _sc_batter_row(683011, 545, 0.320, 90.5,  140, 0.295, 89.8, 405, 0.329, 90.7),
    _sc_batter_row(683002, 620, 0.305, 88.2,  170, 0.315, 88.7, 450, 0.301, 88.0),
    _sc_batter_row(669224, 495, 0.325, 90.0,  125, 0.290, 89.2, 370, 0.337, 90.3),
    _sc_batter_row(663837, 260, 0.300, 87.5,   70, 0.275, 87.0, 190, 0.309, 87.7),
    _sc_batter_row(514888, 655, 0.335, 89.3,  175, 0.350, 89.8, 480, 0.330, 89.1),
    _sc_batter_row(670541, 655, 0.330, 89.2,  175, 0.342, 89.5, 480, 0.326, 89.1),
    _sc_batter_row(670542, 410, 0.395, 94.8,  110, 0.370, 94.0, 300, 0.404, 95.1),
    _sc_batter_row(572233, 545, 0.335, 92.2,  155, 0.340, 92.5, 390, 0.333, 92.1),
    _sc_batter_row(665161, 570, 0.305, 89.0,  155, 0.320, 89.4, 415, 0.300, 88.8),
    _sc_batter_row(673237, 505, 0.318, 91.0,  140, 0.333, 91.3, 365, 0.312, 90.9),
    _sc_batter_row(676801, 295, 0.305, 90.0,   80, 0.315, 90.3, 215, 0.301, 89.9),
    _sc_batter_row(643289, 475, 0.295, 88.0,  130, 0.305, 88.3, 345, 0.291, 87.9),
    _sc_batter_row(676694, 375, 0.290, 87.2,  100, 0.300, 87.5, 275, 0.286, 87.1),
])


def _sc_pitcher_row(pid, pa, xwoba, ev, pa_l, x_l, ev_l, pa_r, x_r, ev_r):
    return {
        "pitcher": pid,
        "PA": pa, "xwOBA": xwoba, "EV50": ev, "BBE": int(pa * 0.72),
        "PA_vs_L": pa_l, "xwOBA_vs_L": x_l, "EV50_vs_L": ev_l, "BBE_vs_L": int(pa_l * 0.72),
        "PA_vs_R": pa_r, "xwOBA_vs_R": x_r, "EV50_vs_R": ev_r, "BBE_vs_R": int(pa_r * 0.72),
    }


SC_PITCHERS = pd.DataFrame([
    # Max Fried (LHP): much tougher on LHB (short track record but strong splits).
    _sc_pitcher_row(608331, 730, 0.295, 88.0, 180, 0.255, 86.8, 550, 0.308, 88.4),
    # Framber Valdez (LHP): big sinkerballer, good vs both, slight LHB advantage.
    _sc_pitcher_row(664285, 780, 0.303, 88.4, 175, 0.268, 87.2, 605, 0.313, 88.7),
])


MLBAM_BY_NAME = {
    "Aaron Judge": 592450, "Giancarlo Stanton": 519203, "Paul Goldschmidt": 572761,
    "Cody Bellinger": 665742, "Anthony Santander": 641355, "Jazz Chisholm Jr.": 683011,
    "Anthony Volpe": 683002, "Austin Wells": 669224, "Trent Grisham": 663837,
    "Jose Altuve": 514888, "Isaac Paredes": 670541, "Yordan Alvarez": 670542,
    "Christian Walker": 572233, "Jeremy Pena": 665161, "Yainer Diaz": 673237,
    "Cam Smith": 676801, "Mauricio Dubon": 643289, "Jake Meyers": 676694,
    "Max Fried": 608331, "Framber Valdez": 664285,
}


BULLPEN = pd.DataFrame([
    {"Team": "NYY", "TBF": 2050, "wOBA": 0.289, "FIP-": 88},
    {"Team": "HOU", "TBF": 2130, "wOBA": 0.305, "FIP-": 96},
])


def install() -> None:
    """Patch all data-fetching seams with fixture returns."""
    from .data import bullpen, fangraphs, schedule, statcast, weather

    schedule.yankees_game_on = lambda d: GAME
    schedule.projected_lineup = _lineup_for
    schedule.last_known_lineup = lambda tid, d, lookback_days=10: _lineup_for(None, tid)
    schedule.pitcher_throws = lambda pid: PITCHER_THROWS.get(pid)
    schedule.venue_location = lambda vid: {
        "lat": 29.7573, "lon": -95.3555, "city": "Houston", "state": "TX",
    }

    # Daikin Park is a dome → weather is neutral; return None to trigger the
    # DOMES short-circuit in weather.multiplier.
    weather.fetch = lambda lat, lon, on: None

    fangraphs.batters = lambda s, qual=1: FG_BATTERS
    fangraphs.pitchers = lambda s, qual=1: FG_PITCHERS

    statcast.batter_aggregates = lambda s: SC_BATTERS
    statcast.pitcher_aggregates = lambda s: SC_PITCHERS
    statcast.lookup_mlbam = lambda name: MLBAM_BY_NAME.get(name)

    bullpen.team_bullpen = lambda s: BULLPEN


def _lineup_for(_game_pk: Optional[int], team_id: int) -> list[dict]:
    if team_id == 147:
        return NYY_LINEUP
    if team_id == 117:
        return HOU_LINEUP
    return []
