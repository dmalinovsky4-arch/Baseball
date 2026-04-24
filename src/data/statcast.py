"""Statcast batter/pitcher aggregates via pybaseball.

For each season we pull the full season's pitch-level data once and cache it,
then derive per-player xwOBA and EV50 (median exit velocity on batted balls).
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from .cache import cached


def _import_pyb():
    import pybaseball
    return pybaseball


def _season_statcast(season: int) -> pd.DataFrame:
    def fetch():
        pyb = _import_pyb()
        start = f"{season}-03-15"
        today = date.today()
        end_dt = date(season, 11, 5)
        if today < end_dt:
            end_dt = today
        end = end_dt.isoformat()
        df = pyb.statcast(start_dt=start, end_dt=end)
        keep = [
            "game_date",
            "batter",
            "pitcher",
            "events",
            "estimated_woba_using_speedangle",
            "woba_value",
            "launch_speed",
            "type",
            "description",
        ]
        keep = [c for c in keep if c in df.columns]
        return df[keep]

    return cached(f"statcast_{season}", fetch)


def batter_aggregates(season: int) -> pd.DataFrame:
    """Per-batter xwOBA and EV50 for `season`."""
    def build():
        df = _season_statcast(season)
        return _aggregate(df, id_col="batter")

    return cached(f"statcast_batters_{season}", build)


def pitcher_aggregates(season: int) -> pd.DataFrame:
    """Per-pitcher xwOBA allowed and EV50 allowed for `season`."""
    def build():
        df = _season_statcast(season)
        return _aggregate(df, id_col="pitcher")

    return cached(f"statcast_pitchers_{season}", build)


def _aggregate(df: pd.DataFrame, id_col: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=[id_col, "xwOBA", "EV50", "PA", "BBE"])

    pa_mask = df["woba_value"].notna()
    pa = df[pa_mask].groupby(id_col).size().rename("PA")

    xwoba = (
        df[pa_mask]
        .groupby(id_col)["estimated_woba_using_speedangle"]
        .mean()
        .rename("xwOBA")
    )

    bbe = df[df["launch_speed"].notna()]
    ev50 = bbe.groupby(id_col)["launch_speed"].median().rename("EV50")
    bbe_count = bbe.groupby(id_col).size().rename("BBE")

    out = pd.concat([pa, xwoba, ev50, bbe_count], axis=1).reset_index()
    return out


def lookup_mlbam(name: str) -> int | None:
    """Resolve a player name to their MLBAM ID via pybaseball."""
    def fetch():
        pyb = _import_pyb()
        parts = name.strip().split()
        if len(parts) < 2:
            return None
        first, last = parts[0], " ".join(parts[1:])
        res = pyb.playerid_lookup(last, first)
        if res is None or len(res) == 0:
            return None
        res = res.sort_values("mlb_played_last", ascending=False, na_position="last")
        return int(res.iloc[0]["key_mlbam"])

    return cached(f"mlbam_{name.lower().replace(' ', '_')}", fetch)


def row_for(agg: pd.DataFrame, mlbam_id: int | None, id_col: str) -> dict | None:
    if agg is None or agg.empty or mlbam_id is None:
        return None
    match = agg[agg[id_col] == mlbam_id]
    if match.empty:
        return None
    r = match.iloc[0]
    return {
        "PA": _num(r.get("PA"), 0),
        "xwOBA": _num(r.get("xwOBA")),
        "EV50": _num(r.get("EV50")),
    }


def _num(v, default=None):
    try:
        if v is None or pd.isna(v):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default
