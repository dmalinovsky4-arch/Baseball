"""Game-time weather via Open-Meteo (no API key required).

Simple run multiplier:
- Temperature: ~+1% runs per +10 F above 70 F (warm air carries).
- Wind speed: >=15 mph at open-air parks bumps carry ~1%; <=5 trims it ~0.5%.
  We don't model orientation (dimensions drive most park variance already,
  see data/park_factors.csv).
- Domes / closed roofs → neutral (multiplier = 1.00).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import requests

DOMES = {
    "Tropicana Field",
    "Rogers Centre",
    "Minute Maid Park",
    "Daikin Park",
    "Chase Field",
    "loanDepot park",
    "American Family Field",
    "T-Mobile Park",
    "Globe Life Field",
}


def fetch(lat: float, lon: float, on: date) -> Optional[dict]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,wind_speed_10m",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "start_date": on.isoformat(),
        "end_date": on.isoformat(),
        "timezone": "America/New_York",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json().get("hourly", {})
    except requests.RequestException:
        return None

    times = data.get("time", [])
    temps = data.get("temperature_2m", [])
    winds = data.get("wind_speed_10m", [])
    idx = min(range(len(times)), key=lambda i: abs(int(times[i][-5:-3]) - 19)) if times else None
    if idx is None:
        return None
    return {
        "temp_f": temps[idx] if idx < len(temps) else None,
        "wind_mph": winds[idx] if idx < len(winds) else None,
    }


def multiplier(venue_name: str, w: Optional[dict]) -> float:
    if venue_name in DOMES or w is None:
        return 1.00
    mult = 1.00
    temp = w.get("temp_f")
    wind = w.get("wind_mph")
    if temp is not None:
        mult *= 1.0 + ((temp - 70.0) / 10.0) * 0.01
    if wind is not None:
        if wind >= 15:
            mult *= 1.01
        elif wind <= 5:
            mult *= 0.995
    return max(0.90, min(1.10, mult))
