"""Formatted console report for a Yankees matchup projection."""

from __future__ import annotations

from typing import Iterable


def _fmt_pct(p: float) -> str:
    return f"{p * 100:5.1f}%"


def render(result: dict) -> str:
    lines: list[str] = []
    g = result["game"]
    w = result.get("weather")
    park = result["park_factor"]

    lines.append("=" * 86)
    lines.append(
        f"YANKEES PROJECTION — {g['date']}  |  {g['away_team']} @ {g['home_team']}"
    )
    park_line = f"Venue: {g['venue_name']}   Runs: {park:.2f}"
    if result.get("venue_known"):
        park_line += (
            f"   HR L/R: {result['park_hr_L']:.2f}/{result['park_hr_R']:.2f}"
            f"   Hits L/R: {result['park_hits_L']:.2f}/{result['park_hits_R']:.2f}"
        )
    else:
        park_line += "   (venue missing from park_factors.csv — neutral fallback)"
    lines.append(park_line)
    if w:
        lines.append(
            f"Weather: {_n(w.get('temp_f'), 0)}°F  "
            f"wind {_n(w.get('wind_mph'), 0)} mph  "
            f"mult {result['weather_mult']:.3f}"
        )
    else:
        lines.append("Weather: n/a (dome or fetch failed)")
    lines.append("")

    sp_hand_opp = result.get("opposing_sp_throws") or "?"
    sp_hand_nyy = result.get("yankees_sp_throws") or "?"
    lines.append(
        f"Yankees SP: {result['yankees_sp']} ({sp_hand_nyy})    "
        f"Opp SP: {result['opposing_sp']} ({sp_hand_opp})"
    )
    lines.append("")

    nyy = result["yankees"]
    opp = result["opponent"]
    lines.append(
        f"Projected runs — NYY {nyy['expected_runs']:.2f}  "
        f"vs  {opp['team']} {opp['expected_runs']:.2f}"
    )
    lines.append(
        f"Yankees win probability: {_fmt_pct(result['yankees_win_pct'])}   "
        f"Total: {nyy['expected_runs'] + opp['expected_runs']:.2f}"
    )
    lines.append("")

    lines.append(f"Yankees lineup vs {result['opposing_sp']}")
    lines.append(_lineup_header())
    lines.extend(_lineup_rows(nyy["lineup"]))
    lines.append("")

    lines.append(f"{opp['team']} lineup vs {result['yankees_sp']}")
    lines.append(_lineup_header())
    lines.extend(_lineup_rows(opp["lineup"]))
    lines.append("=" * 86)
    return "\n".join(lines)


def _lineup_header() -> str:
    return (
        f"{'#':>2} {'B':>1}/{'vs':<2} {'Batter':<22} "
        f"{'mWOBA':>6} {'vSP':>6} {'vBP':>6} "
        f"{'PA':>4} {'H':>5} {'TB':>5} {'HR':>5}"
    )


def _lineup_rows(lineup: Iterable[dict]) -> list[str]:
    rows = []
    for i, row in enumerate(lineup, start=1):
        props = row.get("props", {})
        bats = (row.get("bats") or "?")[0]
        stand = (row.get("stand_vs_sp") or "?")[0]
        rows.append(
            f"{i:>2} {bats}/{stand:<2} {row['name'][:22]:<22} "
            f"{row['matchup_wOBA']:>6.3f} "
            f"{row.get('sp_matchup_wOBA', 0):>6.3f} "
            f"{row.get('bp_matchup_wOBA', 0):>6.3f} "
            f"{props.get('exp_PA', 0):>4.1f} "
            f"{_f(props.get('exp_hits')):>5} "
            f"{_f(props.get('exp_tb')):>5} "
            f"{_f(props.get('exp_hr'), digits=2):>5}"
        )
    return rows


def _f(v, digits: int = 2) -> str:
    if v is None:
        return "  -  "
    return f"{v:.{digits}f}"


def _n(v, digits: int = 1) -> str:
    if v is None:
        return "?"
    return f"{v:.{digits}f}"
