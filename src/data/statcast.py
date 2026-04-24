"""Statcast batter/pitcher aggregates via pybaseball.

For each season we pull the full season's pitch-level data once and cache it,
then derive per-player xwOBA and EV50 (median exit velocity on batted balls).

Aggregates are produced three ways:
  - overall
  - vs LHP (for batters) / vs LHB (for pitchers)
  - vs RHP (for batters) / vs RHB (for pitchers)
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
            "stand",
            "p_throws",
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
    def build():
        df = _season_statcast(season)
        overall = _aggregate(df, id_col="batter", suffix="")
        vs_l = _aggregate(df[df.get("p_throws") == "L"], id_col="batter", suffix="_vs_L")
        vs_r = _aggregate(df[df.get("p_throws") == "R"], id_col="batter", suffix="_vs_R")
        return _merge(overall, vs_l, vs_r, id_col="batter")

    return cached(f"statcast_batters_v2_{season}", build)


def pitcher_aggregates(season: int) -> pd.DataFrame:
    def build():
        df = _season_statcast(season)
        overall = _aggregate(df, id_col="pitcher", suffix="")
        vs_l = _aggregate(df[df.get("stand") == "L"], id_col="pitcher", suffix="_vs_L")
        vs_r = _aggregate(df[df.get("stand") == "R"], id_col="pitcher", suffix="_vs_R")
        return _merge(overall, vs_l, vs_r, id_col="pitcher")

    return cached(f"statcast_pitchers_v2_{season}", build)


def _aggregate(df: pd.DataFrame, id_col: str, suffix: str) -> pd.DataFrame:
    cols = [f"PA{suffix}", f"xwOBA{suffix}", f"EV50{suffix}", f"BBE{suffix}"]
    if df is None or df.empty:
        return pd.DataFrame(columns=[id_col, *cols])

    pa_mask = df["woba_value"].notna()
    pa = df[pa_mask].groupby(id_col).size().rename(f"PA{suffix}")
    xwoba = (
        df[pa_mask]
        .groupby(id_col)["estimated_woba_using_speedangle"]
        .mean()
        .rename(f"xwOBA{suffix}")
    )
    bbe = df[df["launch_speed"].notna()]
    ev50 = bbe.groupby(id_col)["launch_speed"].median().rename(f"EV50{suffix}")
    bbe_count = bbe.groupby(id_col).size().rename(f"BBE{suffix}")
    return pd.concat([pa, xwoba, ev50, bbe_count], axis=1).reset_index()


def _merge(overall: pd.DataFrame, vs_l: pd.DataFrame, vs_r: pd.DataFrame, id_col: str) -> pd.DataFrame:
    out = overall
    for df in (vs_l, vs_r):
        if df is None or df.empty:
            continue
        out = out.merge(df, on=id_col, how="outer")
    return out


def lookup_mlbam(name: str) -> int | None:
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


def row_for(agg: pd.DataFrame, mlbam_id: int | None, id_col: str, split: str = "") -> dict | None:
    """Return {PA, xwOBA, EV50} for a player, optionally pulling a split.

    split: "" (overall), "_vs_L", or "_vs_R"
    Falls back to overall if the split's PA sample is too small (<40).
    """
    if agg is None or agg.empty or mlbam_id is None:
        return None
    match = agg[agg[id_col] == mlbam_id]
    if match.empty:
        return None
    r = match.iloc[0]

    def pick(col: str):
        return _num(r.get(f"{col}{split}")) if split else _num(r.get(col))

    pa = pick("PA") or 0
    xwoba = pick("xwOBA")
    ev50 = pick("EV50")
    if split and (pa < 40 or xwoba is None):
        pa = _num(r.get("PA")) or 0
        xwoba = _num(r.get("xwOBA"))
        ev50 = _num(r.get("EV50"))
    return {"PA": pa, "xwOBA": xwoba, "EV50": ev50}


def overall_xwoba(agg: pd.DataFrame, mlbam_id: int | None, id_col: str) -> float | None:
    if agg is None or agg.empty or mlbam_id is None:
        return None
    match = agg[agg[id_col] == mlbam_id]
    if match.empty:
        return None
    return _num(match.iloc[0].get("xwOBA"))


def _num(v, default=None):
    try:
        if v is None or pd.isna(v):
            return default
        return float(v)
    except (TypeError, ValueError):
        return default
