"""Travel time. Mock mode gives stable numbers for demos; live mode uses the Google Routes API.
If a live call fails for any reason we fall back to mock and say so in the result."""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

from daypilot.timeutil import now

MODES = {"drive": "DRIVE", "transit": "TRANSIT", "walk": "WALK", "bicycle": "BICYCLE"}

# minutes by mode, keyed by a word found in the destination address
MOCK_ROUTES = {
    "jayanagar": {"drive": 25, "transit": 40, "walk": 75, "bicycle": 30},
    "indiranagar": {"drive": 35, "transit": 50, "walk": 110, "bicycle": 45},
    "koramangala": {"drive": 40, "transit": 55, "walk": 120, "bicycle": 50},
    "majestic": {"drive": 30, "transit": 35, "walk": 100, "bicycle": 40},
}
MOCK_DEFAULT = {"drive": 25, "transit": 40, "walk": 60, "bicycle": 30}


def _mock(destination: str, mode: str) -> dict:
    table = MOCK_DEFAULT
    for key, row in MOCK_ROUTES.items():
        if key in destination.lower():
            table = row
            break
    minutes = table[mode]
    speed = {"drive": 30, "transit": 22, "walk": 4.5, "bicycle": 14}[mode]
    return {"duration_min": minutes, "distance_km": round(minutes / 60 * speed, 1), "source": "mock"}


def _live(origin: str, destination: str, depart_at: datetime, mode: str) -> dict:
    key = os.environ["GOOGLE_MAPS_API_KEY"]
    earliest = now() + timedelta(minutes=2)
    when = max(depart_at, earliest).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {
        "origin": {"address": origin},
        "destination": {"address": destination},
        "travelMode": MODES[mode],
        "departureTime": when,
    }
    if mode == "drive":
        body["routingPreference"] = "TRAFFIC_AWARE"
    req = urllib.request.Request(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    route = data["routes"][0]
    seconds = int(route["duration"].rstrip("s"))
    return {
        "duration_min": max(1, round(seconds / 60)),
        "distance_km": round(route.get("distanceMeters", 0) / 1000, 1),
        "source": "google_routes_live",
    }


def get_travel(origin: str, destination: str, depart_at: datetime, mode: str = "transit") -> dict:
    if mode not in MODES:
        raise ValueError(f"Travel mode must be one of: {', '.join(MODES)}.")
    if not origin or not destination:
        raise ValueError("I need both a starting point and a destination.")
    if os.environ.get("GOOGLE_MAPS_API_KEY") and os.environ.get("MAPS_MODE", "live") != "mock":
        try:
            return _live(origin, destination, depart_at, mode)
        except Exception as exc:  # network, quota, bad key: never break the plan
            result = _mock(destination, mode)
            result["source"] = f"mock (live lookup failed: {type(exc).__name__})"
            return result
    return _mock(destination, mode)
