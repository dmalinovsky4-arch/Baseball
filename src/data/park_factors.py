"""Static park-factor lookup. Values are roughly the 2023-2025 3-year
run index from Baseball Savant / FG (100 = league average). `cf_bearing_deg`
is the compass bearing from home plate to center field (degrees, 0 = north,
90 = east). Edit data/park_factors.csv to tune without touching code.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

_CSV = Path(__file__).resolve().parents[2] / "data" / "park_factors.csv"


@lru_cache(maxsize=1)
def _load() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not _CSV.exists():
        return out
    with _CSV.open() as f:
        for row in csv.DictReader(f):
            out[row["venue"].strip().lower()] = {
                "run_factor": float(row["run_factor"]),
                "cf_bearing_deg": float(row.get("cf_bearing_deg") or 0),
            }
    return out


def run_factor(venue_name: str) -> float:
    rec = _load().get((venue_name or "").strip().lower())
    return rec["run_factor"] if rec else 1.00


def cf_bearing(venue_name: str) -> float | None:
    rec = _load().get((venue_name or "").strip().lower())
    return rec["cf_bearing_deg"] if rec else None
