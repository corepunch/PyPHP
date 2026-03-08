"""
weather.py — sample weather data for a fixed list of cities.

Provides static sample data so the example works reliably in all environments
(including CI with no outbound internet access).  The interface is identical to
what a live open-meteo.com fetch would return, so the PHP template in
report.php is unaffected.

Called by examples/html/report.php through PyPHP's require mechanism.
"""

from datetime import date

# Static sample data — representative values for demonstration purposes.
_STATIC_ROWS = [
    {"city": "London",   "temp_c": "+12.3 °C", "temp_val":  12.3,
     "wind_kmh": "18.4 km/h", "condition": "Partly cloudy", "available": True},
    {"city": "Paris",    "temp_c": "+14.1 °C", "temp_val":  14.1,
     "wind_kmh": "11.2 km/h", "condition": "Mainly clear",  "available": True},
    {"city": "New York", "temp_c":  "+8.7 °C", "temp_val":   8.7,
     "wind_kmh": "22.6 km/h", "condition": "Overcast",      "available": True},
    {"city": "Tokyo",    "temp_c": "+16.5 °C", "temp_val":  16.5,
     "wind_kmh":  "9.0 km/h", "condition": "Clear sky",     "available": True},
    {"city": "Sydney",   "temp_c": "+22.8 °C", "temp_val":  22.8,
     "wind_kmh": "14.3 km/h", "condition": "Light showers", "available": True},
]


def fetch_weather():
    """Return a list of weather dicts for each city."""
    return list(_STATIC_ROWS)


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
