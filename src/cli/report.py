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

    lines.append("=" * 78)
    lines.append(
        f"YANKEES PROJECTION — {g['date']}  |  {g['away_team']} @ {g['home_team']}"
    )
    lines.append(f"Venue: {g['venue_name']}   Park factor: {park:.2f}")
    if w:
        lines.append(
            f"Weather: {w.get('temp_f'):.0f}°F  "
            f"wind {w.get('wind_mph'):.0f} mph  "
            f"mult {result['weather_mult']:.2f}"
        )
    else:
        lines.append("Weather: n/a (dome or fetch failed)")
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
    lines.append("=" * 78)
    return "\n".join(lines)


def _lineup_header() -> str:
    return (
        f"{'#':>2}  {'Batter':<22} {'mWOBA':>6} {'PA':>4} "
        f"{'H':>5} {'TB':>5} {'HR':>5}"
    )


def _lineup_rows(lineup: Iterable[dict]) -> list[str]:
    rows = []
    for i, row in enumerate(lineup, start=1):
        props = row.get("props", {})
        rows.append(
            f"{i:>2}  {row['name'][:22]:<22} "
            f"{row['matchup_wOBA']:>6.3f} "
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
