"""Lightweight on-disk cache for slow third-party calls (FanGraphs, Statcast)."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any, Callable

CACHE_DIR = Path(__file__).resolve().parents[2] / ".cache"


def cached(key: str, fn: Callable[[], Any]) -> Any:
    CACHE_DIR.mkdir(exist_ok=True)
    path = CACHE_DIR / f"{key}.pkl"
    if path.exists():
        with path.open("rb") as f:
            return pickle.load(f)
    value = fn()
    with path.open("wb") as f:
        pickle.dump(value, f)
    return value
