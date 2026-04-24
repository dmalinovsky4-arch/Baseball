"""Game-time weather via Open-Meteo (no API key required).

Run multiplier combines three effects:
- Temperature: ~+1% runs per +10 F above 70 F (warm air = more carry).
- Wind magnitude projected onto the home-plate -> CF axis:
    dot = cos(wind_dir_deg - cf_bearing_deg) * wind_mph
    positive dot  -> wind blowing OUT to CF (carry boost)
    negative dot  -> wind blowing IN from CF (suppression)
  Each +10 mph of true tailwind adds ~3% runs; same magnitude the other way
  removes ~3%.
- Domes / closed roofs -> neutral (multiplier = 1.00).

Wind direction returned by Open-Meteo is the bearing the wind is coming FROM
(meteorological convention). We add 180 to get the direction it's blowing
TO before projecting onto the CF axis.
"""

from __future__ import annotations

import math
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
        "hourly": "temperature_2m,wind_speed_10m,wind_direction_10m",
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
    dirs = data.get("wind_direction_10m", [])
    idx = min(range(len(times)), key=lambda i: abs(int(times[i][-5:-3]) - 19)) if times else None
    if idx is None:
        return None
    return {
        "temp_f": temps[idx] if idx < len(temps) else None,
        "wind_mph": winds[idx] if idx < len(winds) else None,
        "wind_from_deg": dirs[idx] if idx < len(dirs) else None,
    }


def multiplier(venue_name: str, w: Optional[dict], cf_bearing_deg: Optional[float]) -> float:
    if venue_name in DOMES or w is None:
        return 1.00
    mult = 1.00
    temp = w.get("temp_f")
    wind = w.get("wind_mph")
    wind_from = w.get("wind_from_deg")

    if temp is not None:
        mult *= 1.0 + ((temp - 70.0) / 10.0) * 0.01

    if wind is not None and wind_from is not None and cf_bearing_deg is not None:
        wind_to = (wind_from + 180.0) % 360.0
        delta = math.radians(wind_to - cf_bearing_deg)
        dot = math.cos(delta) * wind
        mult *= 1.0 + (dot / 10.0) * 0.03
    elif wind is not None:
        if wind >= 15:
            mult *= 1.01
        elif wind <= 5:
            mult *= 0.995

    return max(0.85, min(1.15, mult))
