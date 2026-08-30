"""
FloatChat AI — Geo Utilities

WHY this module?
  The old geo.py computed haversine distance mathematically.
  Now PostGIS handles distance queries, but we still need:
  1. City → lat/lon lookup (for natural language queries like "near Mumbai")
  2. ARGO region inference (classifying coordinates to named ocean regions)

WHY a static city lookup dict instead of a geocoding API?
  - No latency / network dependency
  - No API key needed
  - Our user base is marine scientists querying Indian Ocean ports
  - The set of cities they mention is finite and predictable
"""
from __future__ import annotations
from typing import Optional, Dict, Any

# ── Indian Ocean port / city lookup ──────────────────────────────────────────
_CITIES: Dict[str, Dict[str, float]] = {
    # Indian coast (west)
    "mumbai":        {"lat": 19.076, "lon": 72.877},
    "kochi":         {"lat": 9.931,  "lon": 76.267},
    "goa":           {"lat": 15.492, "lon": 73.818},
    "mangalore":     {"lat": 12.914, "lon": 74.854},
    "kozhikode":     {"lat": 11.258, "lon": 75.780},
    "calicut":       {"lat": 11.258, "lon": 75.780},
    "thiruvananthapuram": {"lat": 8.524, "lon": 76.936},
    "trivandrum":    {"lat": 8.524, "lon": 76.936},
    "ratnagiri":     {"lat": 16.994, "lon": 73.300},
    # Indian coast (east)
    "chennai":       {"lat": 13.082, "lon": 80.270},
    "visakhapatnam": {"lat": 17.686, "lon": 83.218},
    "vizag":         {"lat": 17.686, "lon": 83.218},
    "paradip":       {"lat": 20.316, "lon": 86.609},
    "kolkata":       {"lat": 22.572, "lon": 88.364},
    "puducherry":    {"lat": 11.934, "lon": 79.829},
    "pondicherry":   {"lat": 11.934, "lon": 79.829},
    "tuticorin":     {"lat": 8.764,  "lon": 78.135},
    # Sri Lanka
    "colombo":       {"lat": 6.927,  "lon": 79.861},
    # Region centroids (for "near Arabian Sea" type queries)
    "arabian sea":   {"lat": 15.0,   "lon": 60.0},
    "bay of bengal": {"lat": 15.0,   "lon": 88.0},
    "equator":       {"lat": 0.0,    "lon": 77.0},
    "lakshadweep":   {"lat": 10.57,  "lon": 72.64},
    "andaman":       {"lat": 12.0,   "lon": 93.0},
    # International ports (ARGO science collaborators)
    "oman":          {"lat": 21.5,   "lon": 57.5},
    "maldives":      {"lat": 3.2,    "lon": 73.2},
    "reunion":       {"lat": -21.1,  "lon": 55.5},
    "mauritius":     {"lat": -20.3,  "lon": 57.5},
}


def city_lookup(name: str) -> Optional[Dict[str, float]]:
    """Lookup a city/region name and return {lat, lon}."""
    return _CITIES.get(name.lower().strip())


def infer_coast_from_name(text: str) -> Optional[str]:
    """Guess east/west coast from freeform text."""
    tl = text.lower()
    west = ["mumbai","goa","kochi","mangalore","kerala","arabian","lakshadweep","west"]
    east = ["chennai","vizag","visakhapatnam","kolkata","paradip","bay of bengal","east","andaman"]
    if any(w in tl for w in west):
        return "west"
    if any(e in tl for e in east):
        return "east"
    return None


def classify_region(lat: float, lon: float) -> str:
    """
    Classify a lat/lon point into a named Indian Ocean region.
    Returns one of: arabian_sea, bay_of_bengal, equatorial_io,
                    southern_io, red_sea, persian_gulf, indian_ocean
    """
    if 40 <= lon <= 75 and 5 <= lat <= 25:
        return "arabian_sea"
    if 75 <= lon <= 100 and 5 <= lat <= 25:
        return "bay_of_bengal"
    if -5 <= lat <= 5 and 40 <= lon <= 115:
        return "equatorial_io"
    if lat < -30 and 20 <= lon <= 115:
        return "southern_io"
    if 32 <= lon <= 44 and 12 <= lat <= 30:
        return "red_sea"
    if 48 <= lon <= 60 and 22 <= lat <= 30:
        return "persian_gulf"
    return "indian_ocean"
