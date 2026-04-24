"""Marcel-style blending for small early-season samples.

Blended stat = weighted average of current-season, prior-season, and league
mean, weighted by their respective PA/TBF (with the league weight acting as
the regression constant).

For April / early May, prior-year contribution will dominate until current PA
exceeds the regression constant, which is intentional.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

PRIOR_WEIGHT = 0.5
LEAGUE_REG_PA_BATTER = 100
LEAGUE_REG_PA_PITCHER = 60


@dataclass
class Sample:
    pa: float
    value: Optional[float]


def blend(
    current: Sample,
    prior: Optional[Sample],
    league_mean: float,
    reg_pa: int,
) -> float:
    """Return a blended stat value.

    `None` values on current/prior are treated as missing and contribute zero
    weight (their PA is still counted toward 0 because there's no value).
    """
    num = league_mean * reg_pa
    den = reg_pa

    if current is not None and current.value is not None and current.pa > 0:
        num += current.value * current.pa
        den += current.pa

    if prior is not None and prior.value is not None and prior.pa > 0:
        w = PRIOR_WEIGHT * prior.pa
        num += prior.value * w
        den += w

    return num / den if den > 0 else league_mean
