"""Batter-vs-pitcher matchup math.

Each of the four foundational stats (EV50, pwRC+, xwOBA, wOBA) is translated
into an "implied wOBA" space so we can combine them with equal weighting.

Then we apply log5 for ratio stats (wOBA/xwOBA) and multiplicative composition
for rate-index stats (pwRC+ * pitcher index / 100). The batter EV50 vs
pitcher EV50-allowed is treated as a linear delta against league.

Final output per batter PA: an expected matchup wOBA.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..constants import LEAGUE_EV, LEAGUE_WOBA, LEAGUE_XWOBA


@dataclass
class BatterLine:
    name: str
    xwoba: float
    woba: float
    ev50: float
    wrc_plus: float


@dataclass
class PitcherLine:
    name: str
    xwoba_against: float
    woba_against: float
    ev50_allowed: float
    fip_minus: float  # used to derive a pwRC+-allowed-equivalent


def _log5(batter: float, pitcher: float, league: float) -> float:
    """Odds-ratio style log5 for continuous rate stats, clamped >0."""
    return max(0.150, batter + pitcher - league)


def _ev_to_woba(ev: float) -> float:
    """Rough linearization: each +1 mph of EV50 above league ≈ +0.006 wOBA."""
    return LEAGUE_WOBA + (ev - LEAGUE_EV) * 0.006


def _pitcher_wrc_plus_equiv(fip_minus: Optional[float]) -> float:
    """Convert pitcher FIP- (lower better, 100 = avg) into a wRC+-space index
    (higher = more offense allowed). Rough linear mapping.
    """
    if fip_minus is None:
        return 100.0
    return max(40.0, min(160.0, fip_minus))


def _wrc_plus_to_woba(wrc_plus: float) -> float:
    """wRC+ 100 maps to league wOBA; each +10 wRC+ ~ +0.015 wOBA."""
    return LEAGUE_WOBA + ((wrc_plus - 100.0) / 10.0) * 0.015


def matchup_woba(batter: BatterLine, pitcher: PitcherLine) -> dict:
    """Return component and combined matchup wOBA estimates."""
    xwoba_mu = _log5(batter.xwoba, pitcher.xwoba_against, LEAGUE_XWOBA)
    woba_mu = _log5(batter.woba, pitcher.woba_against, LEAGUE_WOBA)

    bat_ev_woba = _ev_to_woba(batter.ev50)
    pit_ev_woba = _ev_to_woba(pitcher.ev50_allowed)
    ev_mu = _log5(bat_ev_woba, pit_ev_woba, LEAGUE_WOBA)

    pit_wrc_equiv = _pitcher_wrc_plus_equiv(pitcher.fip_minus)
    combined_wrc = batter.wrc_plus * (pit_wrc_equiv / 100.0)
    wrc_mu = _wrc_plus_to_woba(combined_wrc)

    combined = (xwoba_mu + woba_mu + ev_mu + wrc_mu) / 4.0

    return {
        "xwOBA_mu": xwoba_mu,
        "wOBA_mu": woba_mu,
        "EV_mu": ev_mu,
        "wRC_mu": wrc_mu,
        "matchup_wOBA": combined,
    }
