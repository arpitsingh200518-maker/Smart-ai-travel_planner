"""
Flight & Location Module — 100% Local / Offline (No External APIs).
Provides offline origin resolution, flight pricing from CSV dataset,
and Google Flights deep-links without network dependencies.
"""
import math
import urllib.parse
from collections import namedtuple
from typing import Dict, Any, Tuple

# Named tuple for flight fares supporting tuple unpacking and named attributes
class FlightFare(namedtuple("FlightFare", ["price_min", "price_max", "duration_str"])):
    @property
    def range_str(self) -> str:
        return f"₹{self.price_min:,} - ₹{self.price_max:,}"


# Pre-cached airport/city coordinates for instant offline lookups
COMMON_HUBS = {
    "delhi": (28.6139, 77.2090, "Delhi", "India"),
    "new delhi": (28.6139, 77.2090, "New Delhi", "India"),
    "mumbai": (19.0760, 72.8777, "Mumbai", "India"),
    "bombay": (19.0760, 72.8777, "Mumbai", "India"),
    "bengaluru": (12.9716, 77.5946, "Bengaluru", "India"),
    "bangalore": (12.9716, 77.5946, "Bengaluru", "India"),
    "chennai": (13.0827, 80.2707, "Chennai", "India"),
    "madras": (13.0827, 80.2707, "Chennai", "India"),
    "kolkata": (22.5726, 88.3639, "Kolkata", "India"),
    "calcutta": (22.5726, 88.3639, "Kolkata", "India"),
    "hyderabad": (17.3850, 78.4867, "Hyderabad", "India"),
    "ahmedabad": (23.0225, 72.5714, "Ahmedabad", "India"),
    "pune": (18.5204, 73.8567, "Pune", "India"),
    "jaipur": (26.9124, 75.7873, "Jaipur", "India"),
    "lucknow": (26.8467, 80.9462, "Lucknow", "India"),
    "prayagraj": (25.4358, 81.8463, "Prayagraj", "India"),
    "allahabad": (25.4358, 81.8463, "Prayagraj", "India"),
    "varanasi": (25.3176, 82.9739, "Varanasi", "India"),
    "patna": (25.5941, 85.1376, "Patna", "India"),
    "chandigarh": (30.7333, 76.7794, "Chandigarh", "India"),
    "mohali": (30.6740, 76.7249, "Mohali", "India"),
    "kochi": (9.9312, 76.2673, "Kochi", "India"),
    "cochin": (9.9312, 76.2673, "Kochi", "India"),
    "goa": (15.2993, 74.1240, "Goa", "India"),
    "srinagar": (34.0837, 74.7973, "Srinagar", "India"),
    "guwahati": (26.1445, 91.7362, "Guwahati", "India"),
    "london": (51.5074, -0.1278, "London", "United Kingdom"),
    "dubai": (25.2048, 55.2708, "Dubai", "UAE"),
    "singapore": (1.3521, 103.8198, "Singapore", "Singapore"),
    "bangkok": (13.7563, 100.5018, "Bangkok", "Thailand"),
    "kuala lumpur": (3.1390, 101.6869, "Kuala Lumpur", "Malaysia"),
    "kathmandu": (27.7172, 85.3240, "Kathmandu", "Nepal"),
    "paris": (48.8566, 2.3522, "Paris", "France"),
    "new york": (40.7128, -74.0060, "New York", "USA"),
    "tokyo": (35.6762, 139.6503, "Tokyo", "Japan"),
    "sydney": (-33.8688, 151.2093, "Sydney", "Australia"),
}

DEFAULT_ORIGIN = {"city": "Delhi", "country": "India", "latitude": 28.6139, "longitude": 77.2090}


def get_current_location() -> Dict[str, Any]:
    """Offline default location provider. Zero external API calls."""
    return DEFAULT_ORIGIN.copy()


def resolve_location(place_name: str) -> Tuple[float, float, str, str]:
    """Offline city resolution from local dictionary. Zero external API calls."""
    cleaned = (place_name or "").strip()
    if not cleaned or cleaned.lower() in ("anywhere", "not specified", "current location", "my location", "here", "default"):
        return DEFAULT_ORIGIN["latitude"], DEFAULT_ORIGIN["longitude"], DEFAULT_ORIGIN["city"], DEFAULT_ORIGIN["country"]

    key = cleaned.lower()
    if key in COMMON_HUBS:
        return COMMON_HUBS[key]

    # Offline fallback to default origin with user's requested place name
    return DEFAULT_ORIGIN["latitude"], DEFAULT_ORIGIN["longitude"], cleaned.title(), DEFAULT_ORIGIN["country"]


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two coordinates in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calculate_flight_fare(distance_km: float, is_international: bool = False) -> FlightFare:
    """Offline aviation formula for flight fare ranges based on distance."""
    dist = max(30.0, distance_km)
    total_hours = (dist / 750.0) + 0.6
    hrs = int(total_hours)
    mins = int(round((total_hours - hrs) * 60 / 5) * 5)
    if mins == 60:
        hrs += 1
        mins = 0
    duration_str = f"{hrs}h {mins}m" if mins > 0 else f"{hrs}h"

    if not is_international:
        if dist < 450:
            base_price = 2200 + (dist * 2.1)
            min_factor, max_factor = 0.78, 2.35
        elif dist < 1200:
            base_price = 3200 + (dist * 1.85)
            min_factor, max_factor = 0.70, 2.25
        elif dist < 2200:
            base_price = 4200 + (dist * 1.65)
            min_factor, max_factor = 0.68, 2.05
        else:
            base_price = 5500 + (dist * 1.55)
            min_factor, max_factor = 0.72, 2.00
    else:
        if dist < 2500:
            base_price = 7500 + (dist * 2.5)
            min_factor, max_factor = 0.75, 2.15
        elif dist < 5000:
            base_price = 11000 + (dist * 2.2)
            min_factor, max_factor = 0.75, 2.10
        elif dist < 8000:
            base_price = 24000 + (dist * 2.6)
            min_factor, max_factor = 0.78, 2.15
        else:
            base_price = 38000 + (dist * 2.8)
            min_factor, max_factor = 0.80, 2.10

    min_price = int(round((base_price * min_factor) / 100.0) * 100)
    max_price = int(round((base_price * max_factor) / 100.0) * 100)
    min_price = max(1800, min_price)
    max_price = max(min_price + 1500, max_price)
    return FlightFare(min_price, max_price, duration_str)


def get_live_flight_quote(origin_input: str, destination: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get flight quote directly from CSV dataset values with offline distance calculation.
    Zero external APIs called.
    """
    orig_lat, orig_lon, origin_city, origin_country = resolve_location(origin_input)

    try:
        dest_lat = float(destination.get("latitude", 0.0))
        dest_lon = float(destination.get("longitude", 0.0))
    except (ValueError, TypeError):
        dest_lat, dest_lon = 28.6139, 77.2090

    dest_name = str(destination.get("name", "Destination"))
    dest_country = str(destination.get("country", "India"))
    scope = str(destination.get("scope", "domestic")).lower()
    is_international = (scope == "international") or (origin_country and dest_country and origin_country.lower() != dest_country.lower())

    dist_km = haversine_distance_km(orig_lat, orig_lon, dest_lat, dest_lon)

    # Read market price directly from destination CSV dataset
    if "flight_price_min" in destination and "flight_price_max" in destination:
        price_min = int(float(destination["flight_price_min"]))
        price_max = int(float(destination["flight_price_max"]))
        duration_str = str(destination.get("flight_duration", "2h 15m"))
    elif "transport_per_person" in destination:
        price_min = int(float(destination["transport_per_person"]))
        price_max = int(round(price_min * 2.4 / 100) * 100)
        duration_str = str(destination.get("flight_duration", "2h 15m"))
    else:
        fare = calculate_flight_fare(dist_km, is_international)
        price_min, price_max, duration_str = fare.price_min, fare.price_max, fare.duration_str

    query = f"Flights from {origin_city} to {dest_name}"
    search_url = f"https://www.google.com/travel/flights?q={urllib.parse.quote(query)}"

    return {
        "price_min": price_min,
        "price_max": price_max,
        "price_range_str": f"₹{price_min:,} - ₹{price_max:,}",
        "price_per_person": price_min,
        "origin_city": origin_city,
        "origin_country": origin_country,
        "origin_coordinates": (orig_lat, orig_lon),
        "destination_name": dest_name,
        "destination_country": dest_country,
        "distance_km": int(round(dist_km)),
        "duration_str": duration_str,
        "is_international": is_international,
        "search_url": search_url,
    }
