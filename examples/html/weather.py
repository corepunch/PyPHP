"""
weather.py — fetch current weather for a fixed list of cities via open-meteo.com.

open-meteo.com is a free, open-source weather API that requires no API key.
Called by examples/html/report.php through PyPHP's require mechanism.
"""

import json
import urllib.request
from datetime import date

# WMO Weather interpretation codes (WW) -> human-readable label
_WMO = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain",   63: "Rain",       65: "Heavy rain",
    71: "Light snow",   73: "Snow",       75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers", 81: "Showers",  82: "Heavy showers",
    85: "Snow showers",  86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm + hail", 99: "Thunderstorm + heavy hail",
}

_CITIES = [
    {"name": "London",    "lat":  51.51, "lon":  -0.13},
    {"name": "Paris",     "lat":  48.85, "lon":   2.35},
    {"name": "New York",  "lat":  40.71, "lon": -74.01},
    {"name": "Tokyo",     "lat":  35.69, "lon": 139.69},
    {"name": "Sydney",    "lat": -33.87, "lon": 151.21},
]


def _fetch(city):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={city['lat']}&longitude={city['lon']}"
        "&current=temperature_2m,weather_code,wind_speed_10m"
        "&timezone=UTC"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        cur  = data["current"]
        temp = cur["temperature_2m"]
        wind = cur["wind_speed_10m"]
        code = int(cur["weather_code"])
        return {
            "city":      city["name"],
            "temp_c":    f"{temp:+.1f} °C",
            "temp_val":  temp,
            "wind_kmh":  f"{wind:.1f} km/h",
            "condition": _WMO.get(code, f"Code {code}"),
            "available": True,
        }
    except Exception:
        return {
            "city":      city["name"],
            "temp_c":    "N/A",
            "temp_val":  None,
            "wind_kmh":  "N/A",
            "condition": "Unavailable",
            "available": False,
        }


def fetch_weather():
    """Return a list of weather dicts for each city in _CITIES."""
    return [_fetch(c) for c in _CITIES]


def weather_summary(rows):
    """Derive KPI summary cards from a list of weather row dicts."""
    available = [r for r in rows if r["available"]]
    if not available:
        hottest = coldest = "N/A"
    else:
        hottest = max(available, key=lambda r: r["temp_val"])["city"]
        coldest = min(available, key=lambda r: r["temp_val"])["city"]
    return [
        {"label": "Cities Monitored", "value": str(len(rows))},
        {"label": "Hottest City",     "value": hottest},
        {"label": "Coldest City",     "value": coldest},
    ]


_today = date.today()
report_date = f"{_today.strftime('%B')} {_today.day}, {_today.year}"
