"""Tie together data fetch + blending + matchup + game model.

The matchup for each batter is split across the opposing starting pitcher
(first ~5 innings, ~55% of lineup PAs) and the opposing bullpen (~45%).

Handedness splits: Statcast provides batter xwOBA/EV50 vs LHP/RHP and pitcher
xwOBA-allowed/EV50-allowed vs LHB/RHB. We pick the split that matches the
matchup; for wOBA and wRC+ (no native splits from FG) we scale the overall
number by the batter's xwOBA-split ratio (split / overall).

Switch hitters (batSide.code == 'S') hit opposite the pitcher's throwing hand.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from .constants import (
    LEAGUE_EV,
    LEAGUE_WOBA,
    LEAGUE_WRC_PLUS,
    LEAGUE_XWOBA,
    YANKEES_TEAM_ID,
)
from .data import bullpen, fangraphs, park_factors, schedule, statcast, weather
from .model.blend import LEAGUE_REG_PA_BATTER, LEAGUE_REG_PA_PITCHER, Sample, blend
from .model.game import (
    batter_props,
    project_team_runs,
    pythagenpat_win_pct,
)
from .model.matchup import BatterLine, PitcherLine, matchup_woba

LEAGUE_FIP_MINUS = 100.0
SP_WEIGHT = 0.55
BULLPEN_WEIGHT = 1.0 - SP_WEIGHT


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

    bp_cur = bullpen.team_bullpen(current_season)
    bp_prior = bullpen.team_bullpen(prior_season)

    yankees_side = "home" if game["yankees_home"] else "away"
    opp_side = "away" if game["yankees_home"] else "home"

    yankees_sp_name = game[f"{yankees_side}_probable"]
    yankees_sp_id = game[f"{yankees_side}_probable_id"]
    opp_sp_name = game[f"{opp_side}_probable"]
    opp_sp_id = game[f"{opp_side}_probable_id"]
    opp_team_id = game[f"{opp_side}_team_id"]
    opp_team_name = game[f"{opp_side}_team"]

    yankees_sp_throws = _safe_throws(yankees_sp_id)
    opp_sp_throws = _safe_throws(opp_sp_id)

    nyy_lineup = schedule.projected_lineup(game["gamePk"], YANKEES_TEAM_ID) or schedule.last_known_lineup(
        YANKEES_TEAM_ID, target
    )
    opp_lineup = schedule.projected_lineup(game["gamePk"], opp_team_id) or schedule.last_known_lineup(
        opp_team_id, target
    )
    if not nyy_lineup or not opp_lineup:
        raise RuntimeError("Not enough lineup information to project this game.")

    opp_sp = _blend_pitcher(opp_sp_name, "R", fg_p_cur, fg_p_prior, sc_p_cur, sc_p_prior)
    nyy_sp = _blend_pitcher(yankees_sp_name, "R", fg_p_cur, fg_p_prior, sc_p_cur, sc_p_prior)
    opp_bp = _blend_bullpen(opp_team_name, bp_cur, bp_prior)
    nyy_bp = _blend_bullpen("New York Yankees", bp_cur, bp_prior)

    nyy_matchups = [
        _build_matchup(b, opp_sp, opp_sp_throws, opp_bp, fg_b_cur, fg_b_prior, sc_b_cur, sc_b_prior)
        for b in nyy_lineup[:9]
    ]
    opp_matchups = [
        _build_matchup(b, nyy_sp, yankees_sp_throws, nyy_bp, fg_b_cur, fg_b_prior, sc_b_cur, sc_b_prior)
        for b in opp_lineup[:9]
    ]

    park = park_factors.run_factor(game["venue_name"])
    cf_bearing = park_factors.cf_bearing(game["venue_name"])
    w = None
    wmult = 1.00
    if game.get("venue_id"):
        loc = schedule.venue_location(game["venue_id"])
        if loc and loc.get("lat") and loc.get("lon"):
            w = weather.fetch(loc["lat"], loc["lon"], target)
            wmult = weather.multiplier(game["venue_name"] or "", w, cf_bearing)

    nyy_proj = project_team_runs(nyy_matchups, park, wmult)
    opp_proj = project_team_runs(opp_matchups, park, wmult)
    nyy_proj.team = "NYY"
    opp_proj.team = opp_team_name

    for row in nyy_proj.lineup:
        row["props"] = batter_props(row)
    for row in opp_proj.lineup:
        row["props"] = batter_props(row)

    return {
        "game": game,
        "yankees_sp": yankees_sp_name or "TBD",
        "yankees_sp_throws": yankees_sp_throws,
        "opposing_sp": opp_sp_name or "TBD",
        "opposing_sp_throws": opp_sp_throws,
        "park_factor": park,
        "cf_bearing_deg": cf_bearing,
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
        "yankees_win_pct": pythagenpat_win_pct(nyy_proj.expected_runs, opp_proj.expected_runs),
    }


def _safe_throws(pid: Optional[int]) -> Optional[str]:
    if not pid:
        return None
    try:
        return schedule.pitcher_throws(pid)
    except Exception:
        return None


def _effective_stand(bat_side: Optional[str], pitcher_throws: Optional[str]) -> Optional[str]:
    if not bat_side:
        return None
    if bat_side == "S":
        if pitcher_throws == "L":
            return "R"
        if pitcher_throws == "R":
            return "L"
        return None
    return bat_side if bat_side in {"L", "R"} else None


def _blend_pitcher(
    name: Optional[str],
    throws_hand: str,
    fg_cur,
    fg_prior,
    sc_cur,
    sc_prior,
) -> PitcherLine:
    """Build the overall (non-split) pitcher line. Splits are applied at
    matchup time by `_build_matchup` via `_pitcher_line_vs_stand`."""
    if not name:
        return PitcherLine("TBD", LEAGUE_XWOBA, LEAGUE_WOBA, LEAGUE_EV, LEAGUE_FIP_MINUS)

    fg_c = fangraphs.pitcher_row(fg_cur, name) or {}
    fg_p = fangraphs.pitcher_row(fg_prior, name) or {}
    mlbam = statcast.lookup_mlbam(name)
    sc_c = statcast.row_for(sc_cur, mlbam, "pitcher") or {}
    sc_p = statcast.row_for(sc_prior, mlbam, "pitcher") or {}

    xwoba = blend(
        Sample(sc_c.get("PA", 0), sc_c.get("xwOBA")),
        Sample(sc_p.get("PA", 0), sc_p.get("xwOBA")) if sc_p else None,
        LEAGUE_XWOBA,
        LEAGUE_REG_PA_PITCHER,
    )
    woba = blend(
        Sample(fg_c.get("TBF", 0), fg_c.get("wOBA")),
        Sample(fg_p.get("TBF", 0), fg_p.get("wOBA")) if fg_p else None,
        LEAGUE_WOBA,
        LEAGUE_REG_PA_PITCHER,
    )
    ev = blend(
        Sample(sc_c.get("PA", 0), sc_c.get("EV50")),
        Sample(sc_p.get("PA", 0), sc_p.get("EV50")) if sc_p else None,
        LEAGUE_EV,
        LEAGUE_REG_PA_PITCHER,
    )
    fip_minus = blend(
        Sample(fg_c.get("TBF", 0), fg_c.get("FIP-")),
        Sample(fg_p.get("TBF", 0), fg_p.get("FIP-")) if fg_p else None,
        LEAGUE_FIP_MINUS,
        LEAGUE_REG_PA_PITCHER,
    )

    line = PitcherLine(
        name=name, xwoba_against=xwoba, woba_against=woba, ev50_allowed=ev, fip_minus=fip_minus
    )
    line._mlbam = mlbam  # type: ignore[attr-defined]
    line._sc_cur = sc_cur  # type: ignore[attr-defined]
    line._sc_prior = sc_prior  # type: ignore[attr-defined]
    line._throws = throws_hand  # type: ignore[attr-defined]
    return line


def _pitcher_line_vs_stand(pitcher: PitcherLine, stand: Optional[str]) -> PitcherLine:
    """Return a copy of `pitcher` with xwOBA/EV50 swapped for the split
    facing the given batter stand. Falls back to the overall line if split
    samples are too small or data is missing.
    """
    if stand not in {"L", "R"} or not hasattr(pitcher, "_mlbam"):
        return pitcher
    split_suffix = f"_vs_{stand}"
    sc_c = statcast.row_for(pitcher._sc_cur, pitcher._mlbam, "pitcher", split=split_suffix) or {}
    sc_p = statcast.row_for(pitcher._sc_prior, pitcher._mlbam, "pitcher", split=split_suffix) or {}

    xwoba = blend(
        Sample(sc_c.get("PA", 0), sc_c.get("xwOBA")),
        Sample(sc_p.get("PA", 0), sc_p.get("xwOBA")) if sc_p else None,
        LEAGUE_XWOBA,
        LEAGUE_REG_PA_PITCHER,
    )
    ev = blend(
        Sample(sc_c.get("PA", 0), sc_c.get("EV50")),
        Sample(sc_p.get("PA", 0), sc_p.get("EV50")) if sc_p else None,
        LEAGUE_EV,
        LEAGUE_REG_PA_PITCHER,
    )
    overall_x = statcast.overall_xwoba(pitcher._sc_cur, pitcher._mlbam, "pitcher") or LEAGUE_XWOBA
    ratio = xwoba / overall_x if overall_x else 1.0
    woba = pitcher.woba_against * ratio

    return PitcherLine(
        name=pitcher.name,
        xwoba_against=xwoba,
        woba_against=woba,
        ev50_allowed=ev,
        fip_minus=pitcher.fip_minus,
    )


def _blend_bullpen(team_name: str, bp_cur, bp_prior) -> PitcherLine:
    cur = bullpen.row_for(bp_cur, team_name) or {}
    prior = bullpen.row_for(bp_prior, team_name) or {}

    woba = blend(
        Sample(cur.get("TBF", 0), cur.get("wOBA")),
        Sample(prior.get("TBF", 0), prior.get("wOBA")) if prior else None,
        LEAGUE_WOBA,
        LEAGUE_REG_PA_PITCHER,
    )
    fip_minus = blend(
        Sample(cur.get("TBF", 0), cur.get("FIP-")),
        Sample(prior.get("TBF", 0), prior.get("FIP-")) if prior else None,
        LEAGUE_FIP_MINUS,
        LEAGUE_REG_PA_PITCHER,
    )
    # Bullpens don't come with a native xwOBA/EV from the FG aggregate; tie
    # them to wOBA-against via league ratios.
    xwoba = LEAGUE_XWOBA * (woba / LEAGUE_WOBA)
    ev = LEAGUE_EV + (woba - LEAGUE_WOBA) * 10.0

    return PitcherLine(
        name=f"{team_name} bullpen",
        xwoba_against=xwoba,
        woba_against=woba,
        ev50_allowed=ev,
        fip_minus=fip_minus,
    )


def _build_matchup(
    batter: dict,
    sp: PitcherLine,
    sp_throws: Optional[str],
    bullpen_line: PitcherLine,
    fg_cur,
    fg_prior,
    sc_cur,
    sc_prior,
) -> dict:
    name = batter.get("name") or ""
    mlbam = batter.get("player_id") or statcast.lookup_mlbam(name)

    fg_c = fangraphs.batter_row(fg_cur, name) or {}
    fg_p = fangraphs.batter_row(fg_prior, name) or {}

    overall_x = statcast.overall_xwoba(sc_cur, mlbam, "batter") or LEAGUE_XWOBA

    def batter_line_vs(throws: Optional[str]) -> BatterLine:
        stand = _effective_stand(batter.get("bats"), throws)
        split_suffix = f"_vs_{throws}" if throws in {"L", "R"} else ""
        sc_c = statcast.row_for(sc_cur, mlbam, "batter", split=split_suffix) or {}
        sc_p = statcast.row_for(sc_prior, mlbam, "batter", split=split_suffix) or {}

        xwoba = blend(
            Sample(sc_c.get("PA", 0), sc_c.get("xwOBA")),
            Sample(sc_p.get("PA", 0), sc_p.get("xwOBA")) if sc_p else None,
            LEAGUE_XWOBA,
            LEAGUE_REG_PA_BATTER,
        )
        ev = blend(
            Sample(sc_c.get("PA", 0), sc_c.get("EV50")),
            Sample(sc_p.get("PA", 0), sc_p.get("EV50")) if sc_p else None,
            LEAGUE_EV,
            LEAGUE_REG_PA_BATTER,
        )
        ratio = xwoba / overall_x if overall_x else 1.0
        woba_overall = blend(
            Sample(fg_c.get("PA", 0), fg_c.get("wOBA")),
            Sample(fg_p.get("PA", 0), fg_p.get("wOBA")) if fg_p else None,
            LEAGUE_WOBA,
            LEAGUE_REG_PA_BATTER,
        )
        wrc_overall = blend(
            Sample(fg_c.get("PA", 0), fg_c.get("wRC+")),
            Sample(fg_p.get("PA", 0), fg_p.get("wRC+")) if fg_p else None,
            LEAGUE_WRC_PLUS,
            LEAGUE_REG_PA_BATTER,
        )
        woba_split = woba_overall * ratio
        wrc_split = wrc_overall * ratio
        return BatterLine(name=name, xwoba=xwoba, woba=woba_split, ev50=ev, wrc_plus=wrc_split), stand

    sp_bl, stand_vs_sp = batter_line_vs(sp_throws)
    sp_effective = _pitcher_line_vs_stand(sp, stand_vs_sp)
    m_sp = matchup_woba(sp_bl, sp_effective)

    # Bullpen split: we don't know individual reliever throw mixes, so we
    # apply the batter's split based on assuming a mostly-RHP bullpen; if
    # batter bats L, that's vs-R; if batter bats R, vs-R too; switch hitters
    # hit L vs RHP. Effectively use bats-vs-R split.
    bp_bl, _ = batter_line_vs("R")
    m_bp = matchup_woba(bp_bl, bullpen_line)

    combined_woba = SP_WEIGHT * m_sp["matchup_wOBA"] + BULLPEN_WEIGHT * m_bp["matchup_wOBA"]

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

    return {
        "name": name,
        "order": batter.get("order"),
        "bats": batter.get("bats"),
        "stand_vs_sp": stand_vs_sp,
        "sp_matchup_wOBA": m_sp["matchup_wOBA"],
        "bp_matchup_wOBA": m_bp["matchup_wOBA"],
        "matchup_wOBA": combined_woba,
        "blended_avg": avg,
        "blended_slg": slg,
        "blended_hr_per_pa": hr_rate,
    }
