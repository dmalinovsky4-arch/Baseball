"""Static park-factor lookup. Values are roughly the 2023-2025 3-year
run index from Baseball Savant / FG (100 = league average). Refine as
needed; edit data/park_factors.csv to tune without touching code.
"""

from __future__ import annotations

import csv
from pathlib import Path

_CSV = Path(__file__).resolve().parents[2] / "data" / "park_factors.csv"


def load() -> dict[str, float]:
    factors: dict[str, float] = {}
    if not _CSV.exists():
        return factors
    with _CSV.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            factors[row["venue"].strip().lower()] = float(row["run_factor"])
    return factors


def run_factor(venue_name: str) -> float:
    factors = load()
    return factors.get((venue_name or "").strip().lower(), 1.00)
