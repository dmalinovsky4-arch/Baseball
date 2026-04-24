"""FanGraphs season batting/pitching leaderboards via pybaseball.

We pull full leaderboards once per season and cache. Keys we care about:
- Batters: wOBA, wRC+, PA
- Pitchers: wOBA (against), FIP-, TBF (batters faced)
"""

from __future__ import annotations

import pandas as pd

from .cache import cached


def _import_pyb():
    import pybaseball  # local import so tests/CLI without pyb installed still parse
    return pybaseball


def batters(season: int, qual: int = 1) -> pd.DataFrame:
    def fetch():
        pyb = _import_pyb()
        df = pyb.batting_stats(season, qual=qual)
        df.columns = [str(c) for c in df.columns]
        return df

    return cached(f"fg_batters_{season}_q{qual}", fetch)


def pitchers(season: int, qual: int = 1) -> pd.DataFrame:
    def fetch():
        pyb = _import_pyb()
        df = pyb.pitching_stats(season, qual=qual)
        df.columns = [str(c) for c in df.columns]
        return df

    return cached(f"fg_pitchers_{season}_q{qual}", fetch)


def batter_row(df: pd.DataFrame, name: str) -> dict | None:
    """Case-insensitive name match. Returns dict of blended-ready columns."""
    if df.empty:
        return None
    mask = df["Name"].str.lower() == name.lower()
    match = df[mask]
    if match.empty:
        return None
    r = match.iloc[0]
    pa = _num(r.get("PA"), 0) or 0
    hr = _num(r.get("HR"), 0) or 0
    return {
        "PA": pa,
        "wOBA": _num(r.get("wOBA")),
        "wRC+": _num(r.get("wRC+")),
        "AVG": _num(r.get("AVG")),
        "SLG": _num(r.get("SLG")),
        "HR_per_PA": (hr / pa) if pa > 0 else None,
    }


def pitcher_row(df: pd.DataFrame, name: str) -> dict | None:
    if df.empty:
        return None
    mask = df["Name"].str.lower() == name.lower()
    match = df[mask]
    if match.empty:
        return None
    r = match.iloc[0]
    return {
        "TBF": _num(r.get("TBF"), 0),
        "wOBA": _num(r.get("wOBA")),
        "FIP-": _num(r.get("FIP-")),
    }


def _num(v, default=None):
    try:
        if v is None or pd.isna(v):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default
