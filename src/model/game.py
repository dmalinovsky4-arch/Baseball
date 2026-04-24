"""Roll batter-level matchup wOBAs up to team runs, then to win probability
and per-batter prop projections.

Run conversion uses the standard wOBA-to-wRC linear formula:
    wRAA / PA = (wOBA - lgwOBA) / wOBA_scale
    wRC / PA  = wRAA/PA + lgR/PA

Lineup PA profile approximates a 9-inning game with the top of the order
getting ~4.6 PAs and the 9-hole ~3.8 PAs.

Park factors enter in three places:
- Team runs: multiply by the venue's overall runs factor.
- Batter exp_hits: scale by hits factor for the batter's effective stand.
- Batter exp_HR:   scale by HR factor for the batter's effective stand.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..constants import LEAGUE_RUNS_PER_PA, LEAGUE_WOBA, PYTHAGENPAT_FLOOR, WOBA_SCALE

LINEUP_PA = [4.60, 4.50, 4.40, 4.30, 4.20, 4.10, 4.00, 3.90, 3.80]


@dataclass
class TeamProjection:
    team: str
    expected_runs: float
    lineup: list[dict]


def woba_to_runs_per_pa(woba: float) -> float:
    return (woba - LEAGUE_WOBA) / WOBA_SCALE + LEAGUE_RUNS_PER_PA


def project_team_runs(
    lineup_matchups: list[dict],
    park_runs: float,
    weather_mult: float,
) -> TeamProjection:
    total_runs = 0.0
    enriched: list[dict] = []
    for i, row in enumerate(lineup_matchups):
        pa = LINEUP_PA[i] if i < len(LINEUP_PA) else 3.8
        rpp = woba_to_runs_per_pa(row["matchup_wOBA"])
        slot_runs = pa * rpp
        total_runs += slot_runs
        enriched.append({**row, "PA": pa, "slot_runs": slot_runs})

    total_runs *= park_runs * weather_mult
    return TeamProjection(
        team=lineup_matchups[0].get("_team", ""),
        expected_runs=total_runs,
        lineup=enriched,
    )


def pythagenpat_win_pct(runs_for: float, runs_against: float) -> float:
    total = runs_for + runs_against
    if total <= 0:
        return 0.5
    exp = max(PYTHAGENPAT_FLOOR, total ** 0.287)
    rf = runs_for ** exp
    ra = runs_against ** exp
    return rf / (rf + ra)


def batter_props(
    row: dict,
    park_hits: float = 1.00,
    park_hr: float = 1.00,
) -> dict:
    """Convert blended rates + matchup wOBA into simple per-game projections,
    applying the park's handedness-specific hits/HR factors on top.
    """
    pa = row["PA"]
    mult = row["matchup_wOBA"] / LEAGUE_WOBA
    avg = row.get("blended_avg")
    slg = row.get("blended_slg")
    hr_rate = row.get("blended_hr_per_pa")

    exp_ab = pa * 0.90
    exp_hits = (avg * exp_ab * mult * park_hits) if avg is not None else None
    # SLG tracks total-bases per AB; scale it by the average of hits and HR
    # park effects as a pragmatic mix (HR drives the tails, hits the volume).
    tb_park = (park_hits + park_hr) / 2.0
    exp_tb = (slg * exp_ab * mult * tb_park) if slg is not None else None
    exp_hr = (hr_rate * pa * mult * park_hr) if hr_rate is not None else None
    return {
        "exp_PA": round(pa, 2),
        "exp_hits": round(exp_hits, 2) if exp_hits is not None else None,
        "exp_tb": round(exp_tb, 2) if exp_tb is not None else None,
        "exp_hr": round(exp_hr, 3) if exp_hr is not None else None,
    }
