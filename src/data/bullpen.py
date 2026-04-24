"""Team bullpen aggregates.

We pull the full FanGraphs pitching leaderboard (already cached by
`fangraphs.pitchers`) and filter to relievers: G - GS >= 10 and
GS / G < 0.3. For each team we produce a TBF-weighted average of
wOBA-against and FIP-, plus a total TBF sample size.
"""

from __future__ import annotations

import pandas as pd

from . import fangraphs

FG_TEAM_ABBR = {
    "Arizona Diamondbacks": "ARI",
    "Atlanta Braves": "ATL",
    "Baltimore Orioles": "BAL",
    "Boston Red Sox": "BOS",
    "Chicago Cubs": "CHC",
    "Chicago White Sox": "CHW",
    "Cincinnati Reds": "CIN",
    "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL",
    "Detroit Tigers": "DET",
    "Houston Astros": "HOU",
    "Kansas City Royals": "KCR",
    "Los Angeles Angels": "LAA",
    "Los Angeles Dodgers": "LAD",
    "Miami Marlins": "MIA",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "New York Mets": "NYM",
    "New York Yankees": "NYY",
    "Oakland Athletics": "OAK",
    "Athletics": "OAK",
    "Philadelphia Phillies": "PHI",
    "Pittsburgh Pirates": "PIT",
    "San Diego Padres": "SDP",
    "San Francisco Giants": "SFG",
    "Seattle Mariners": "SEA",
    "St. Louis Cardinals": "STL",
    "Tampa Bay Rays": "TBR",
    "Texas Rangers": "TEX",
    "Toronto Blue Jays": "TOR",
    "Washington Nationals": "WSN",
}


def _is_reliever(row) -> bool:
    g = _num(row.get("G"), 0)
    gs = _num(row.get("GS"), 0)
    if g <= 0:
        return False
    return (g - gs) >= 10 and (gs / g) < 0.3


def team_bullpen(season: int) -> pd.DataFrame:
    """Return one row per team: {Team, TBF, wOBA, FIP-}."""
    df = fangraphs.pitchers(season)
    if df is None or df.empty or "Team" not in df.columns:
        return pd.DataFrame(columns=["Team", "TBF", "wOBA", "FIP-"])

    rel = df[df.apply(_is_reliever, axis=1)].copy()
    if rel.empty:
        return pd.DataFrame(columns=["Team", "TBF", "wOBA", "FIP-"])

    rel["TBF"] = rel["TBF"].fillna(0)
    grouped = rel.groupby("Team").apply(_weighted, include_groups=False).reset_index()
    return grouped


def _weighted(grp: pd.DataFrame) -> pd.Series:
    tbf = grp["TBF"].sum()
    if tbf <= 0:
        return pd.Series({"TBF": 0, "wOBA": None, "FIP-": None})
    woba = (grp["wOBA"].fillna(0) * grp["TBF"]).sum() / tbf
    fip = (grp["FIP-"].fillna(100) * grp["TBF"]).sum() / tbf
    return pd.Series({"TBF": float(tbf), "wOBA": float(woba), "FIP-": float(fip)})


def row_for(df: pd.DataFrame, team_name: str) -> dict | None:
    if df is None or df.empty:
        return None
    abbr = FG_TEAM_ABBR.get(team_name)
    match = df[df["Team"].str.lower() == (abbr or team_name).lower()]
    if match.empty:
        last = team_name.split()[-1]
        match = df[df["Team"].str.contains(last, case=False, na=False)]
        if match.empty:
            return None
    r = match.iloc[0]
    return {"TBF": _num(r.get("TBF"), 0), "wOBA": _num(r.get("wOBA")), "FIP-": _num(r.get("FIP-"))}


def _num(v, default=None):
    try:
        if v is None or pd.isna(v):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default
