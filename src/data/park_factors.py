"""Park factors lookup.

data/park_factors.csv has one row per venue with columns:
    venue, runs, hr_L, hr_R, hits_L, hits_R

Values are multipliers (1.00 = neutral). HR and hits factors are split by
batter handedness because dimensions favor each side differently
(e.g., Yankee Stadium's short RF porch → hr_L > hr_R; Fenway's Monster →
hits_R > hits_L). Switch hitters should be evaluated using the side they
bat against the actual pitcher (caller handles this).

Edit the CSV directly to tune without touching code.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import Optional

_CSV = Path(__file__).resolve().parents[2] / "data" / "park_factors.csv"

_COLS = ("runs", "hr_L", "hr_R", "hits_L", "hits_R")


@lru_cache(maxsize=1)
def _load() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not _CSV.exists():
        return out
    with _CSV.open() as f:
        for row in csv.DictReader(f):
            out[row["venue"].strip().lower()] = {
                col: float(row.get(col) or 1.0) for col in _COLS
            }
    return out


def _rec(venue_name: str) -> Optional[dict]:
    return _load().get((venue_name or "").strip().lower())


def run_factor(venue_name: str) -> float:
    rec = _rec(venue_name)
    return rec["runs"] if rec else 1.00


def hr_factor(venue_name: str, stand: Optional[str]) -> float:
    rec = _rec(venue_name)
    if not rec:
        return 1.00
    key = "hr_L" if stand == "L" else "hr_R"
    return rec[key]


def hits_factor(venue_name: str, stand: Optional[str]) -> float:
    rec = _rec(venue_name)
    if not rec:
        return 1.00
    key = "hits_L" if stand == "L" else "hits_R"
    return rec[key]


def is_known(venue_name: str) -> bool:
    return (venue_name or "").strip().lower() in _load()
