"""Tie together data fetch + blending + matchup + game model for a Yankees game."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Optional

from .constants import (
    LEAGUE_EV,
    LEAGUE_WOBA,
    LEAGUE_WRC_PLUS,
    LEAGUE_XWOBA,
    YANKEES_TEAM_ID,
)
from .data import fangraphs, park_factors, schedule, statcast, weather
from .model.blend import LEAGUE_REG_PA_BATTER, LEAGUE_REG_PA_PITCHER, Sample, blend
from .model.game import (
    batter_props,
    project_team_runs,
    pythagenpat_win_pct,
)
from .model.matchup import BatterLine, PitcherLine, matchup_woba

LEAGUE_FIP_MINUS = 100.0


def project(target: date, prior_season: int, current_season: int) -> dict:
    game = schedule.yankees_game_on(target)
    if game is None:
        raise RuntimeError(f"No Yankees game scheduled on {target.isoformat()}")

    fg_b_cur = fangraphs.batters(current_season)
    fg_b_prior = fangraphs.batters(prior_season)
    fg_p_cur = fangraphs.pitchers(current_season)
    fg_p_prior = fangraphs.pitchers(prior_season)

    sc_b_cur = statcast.batter_aggregates(current_season)
    sc_b_prior = statcast.batter_aggregates(prior_season)
    sc_p_cur = statcast.pitcher_aggregates(current_season)
    sc_p_prior = statcast.pitcher_aggregates(prior_season)

    yankees_side = "home" if game["yankees_home"] else "away"
    opp_side = "away" if game["yankees_home"] else "home"

    yankees_sp_name = game[f"{yankees_side}_probable"]
    opp_sp_name = game[f"{opp_side}_probable"]
    opp_team_id = game[f"{opp_side}_team_id"]
    opp_team_name = game[f"{opp_side}_team"]

    nyy_lineup = schedule.projected_lineup(game["gamePk"], YANKEES_TEAM_ID)
    if not nyy_lineup:
        nyy_lineup = schedule.last_known_lineup(YANKEES_TEAM_ID, target)
    opp_lineup = schedule.projected_lineup(game["gamePk"], opp_team_id)
    if not opp_lineup:
        opp_lineup = schedule.last_known_lineup(opp_team_id, target)

    opp_sp = _blend_pitcher(opp_sp_name, fg_p_cur, fg_p_prior, sc_p_cur, sc_p_prior)
    nyy_sp = _blend_pitcher(yankees_sp_name, fg_p_cur, fg_p_prior, sc_p_cur, sc_p_prior)

    nyy_matchups = [
        _build_matchup(b, opp_sp, fg_b_cur, fg_b_prior, sc_b_cur, sc_b_prior)
        for b in nyy_lineup[:9]
    ]
    opp_matchups = [
        _build_matchup(b, nyy_sp, fg_b_cur, fg_b_prior, sc_b_cur, sc_b_prior)
        for b in opp_lineup[:9]
    ]

    if not nyy_matchups or not opp_matchups:
        raise RuntimeError("Not enough lineup information to project this game.")

    park = park_factors.run_factor(game["venue_name"])
    w = None
    wmult = 1.00
    if game.get("venue_id"):
        loc = schedule.venue_location(game["venue_id"])
        if loc and loc.get("lat") and loc.get("lon"):
            w = weather.fetch(loc["lat"], loc["lon"], target)
            wmult = weather.multiplier(game["venue_name"] or "", w)

    nyy_proj = project_team_runs(nyy_matchups, park, wmult)
    opp_proj = project_team_runs(opp_matchups, park, wmult)
    nyy_proj.team = "NYY"
    opp_proj.team = opp_team_name

    for row in nyy_proj.lineup:
        row["props"] = batter_props(row)
    for row in opp_proj.lineup:
        row["props"] = batter_props(row)

    win_pct = pythagenpat_win_pct(nyy_proj.expected_runs, opp_proj.expected_runs)

    return {
        "game": game,
        "yankees_sp": yankees_sp_name or "TBD",
        "opposing_sp": opp_sp_name or "TBD",
        "park_factor": park,
        "weather": w,
        "weather_mult": wmult,
        "yankees": {
            "team": nyy_proj.team,
            "expected_runs": nyy_proj.expected_runs,
            "lineup": nyy_proj.lineup,
        },
        "opponent": {
            "team": opp_proj.team,
            "expected_runs": opp_proj.expected_runs,
            "lineup": opp_proj.lineup,
        },
        "yankees_win_pct": win_pct,
    }


def _blend_pitcher(
    name: Optional[str],
    fg_cur,
    fg_prior,
    sc_cur,
    sc_prior,
) -> PitcherLine:
    if not name:
        return PitcherLine("TBD", LEAGUE_XWOBA, LEAGUE_WOBA, LEAGUE_EV, LEAGUE_FIP_MINUS)

    fg_c = fangraphs.pitcher_row(fg_cur, name)
    fg_p = fangraphs.pitcher_row(fg_prior, name)

    mlbam = statcast.lookup_mlbam(name)
    sc_c = statcast.row_for(sc_cur, mlbam, "pitcher")
    sc_p = statcast.row_for(sc_prior, mlbam, "pitcher")

    xwoba = blend(
        Sample((sc_c or {}).get("PA", 0), (sc_c or {}).get("xwOBA")),
        Sample((sc_p or {}).get("PA", 0), (sc_p or {}).get("xwOBA")) if sc_p else None,
        LEAGUE_XWOBA,
        LEAGUE_REG_PA_PITCHER,
    )
    woba = blend(
        Sample((fg_c or {}).get("TBF", 0), (fg_c or {}).get("wOBA")),
        Sample((fg_p or {}).get("TBF", 0), (fg_p or {}).get("wOBA")) if fg_p else None,
        LEAGUE_WOBA,
        LEAGUE_REG_PA_PITCHER,
    )
    ev = blend(
        Sample((sc_c or {}).get("PA", 0), (sc_c or {}).get("EV50")),
        Sample((sc_p or {}).get("PA", 0), (sc_p or {}).get("EV50")) if sc_p else None,
        LEAGUE_EV,
        LEAGUE_REG_PA_PITCHER,
    )
    fip_minus = blend(
        Sample((fg_c or {}).get("TBF", 0), (fg_c or {}).get("FIP-")),
        Sample((fg_p or {}).get("TBF", 0), (fg_p or {}).get("FIP-")) if fg_p else None,
        LEAGUE_FIP_MINUS,
        LEAGUE_REG_PA_PITCHER,
    )

    return PitcherLine(
        name=name,
        xwoba_against=xwoba,
        woba_against=woba,
        ev50_allowed=ev,
        fip_minus=fip_minus,
    )


def _build_matchup(
    batter: dict,
    pitcher: PitcherLine,
    fg_cur,
    fg_prior,
    sc_cur,
    sc_prior,
) -> dict:
    name = batter.get("name") or ""
    mlbam = batter.get("player_id") or statcast.lookup_mlbam(name)

    fg_c = fangraphs.batter_row(fg_cur, name) or {}
    fg_p = fangraphs.batter_row(fg_prior, name) or {}

    sc_c = statcast.row_for(sc_cur, mlbam, "batter") or {}
    sc_p = statcast.row_for(sc_prior, mlbam, "batter") or {}

    xwoba = blend(
        Sample(sc_c.get("PA", 0), sc_c.get("xwOBA")),
        Sample(sc_p.get("PA", 0), sc_p.get("xwOBA")) if sc_p else None,
        LEAGUE_XWOBA,
        LEAGUE_REG_PA_BATTER,
    )
    woba = blend(
        Sample(fg_c.get("PA", 0), fg_c.get("wOBA")),
        Sample(fg_p.get("PA", 0), fg_p.get("wOBA")) if fg_p else None,
        LEAGUE_WOBA,
        LEAGUE_REG_PA_BATTER,
    )
    ev = blend(
        Sample(sc_c.get("PA", 0), sc_c.get("EV50")),
        Sample(sc_p.get("PA", 0), sc_p.get("EV50")) if sc_p else None,
        LEAGUE_EV,
        LEAGUE_REG_PA_BATTER,
    )
    wrc = blend(
        Sample(fg_c.get("PA", 0), fg_c.get("wRC+")),
        Sample(fg_p.get("PA", 0), fg_p.get("wRC+")) if fg_p else None,
        LEAGUE_WRC_PLUS,
        LEAGUE_REG_PA_BATTER,
    )

    avg = blend(
        Sample(fg_c.get("PA", 0), fg_c.get("AVG")),
        Sample(fg_p.get("PA", 0), fg_p.get("AVG")) if fg_p else None,
        0.248,
        LEAGUE_REG_PA_BATTER,
    )
    slg = blend(
        Sample(fg_c.get("PA", 0), fg_c.get("SLG")),
        Sample(fg_p.get("PA", 0), fg_p.get("SLG")) if fg_p else None,
        0.410,
        LEAGUE_REG_PA_BATTER,
    )
    hr_rate = blend(
        Sample(fg_c.get("PA", 0), fg_c.get("HR_per_PA")),
        Sample(fg_p.get("PA", 0), fg_p.get("HR_per_PA")) if fg_p else None,
        0.030,
        LEAGUE_REG_PA_BATTER,
    )

    line = BatterLine(name=name, xwoba=xwoba, woba=woba, ev50=ev, wrc_plus=wrc)
    comp = matchup_woba(line, pitcher)

    return {
        "name": name,
        "order": batter.get("order"),
        "bats": batter.get("bats"),
        "blended_xwOBA": xwoba,
        "blended_wOBA": woba,
        "blended_EV50": ev,
        "blended_wRC+": wrc,
        "blended_avg": avg,
        "blended_slg": slg,
        "blended_hr_per_pa": hr_rate,
        **comp,
    }
