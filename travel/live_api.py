"""
Live Data APIs for Smart AI Travel Planner.
Integrates live real-time APIs for all dataset entries:
- Live Weather & Temperature (Open-Meteo API)
- Live Destination Facts & Photos (Wikipedia REST API)
- Live Currency Exchange Rates (Frankfurter / ExchangeRate API)
- Live Flight Search Deep Links (Google Flights / Skyscanner)
- Live Hotel Search Deep Links (Booking.com / Google Hotels)
"""
import json
import time
import urllib.parse
import urllib.request
from typing import Dict, Any, Optional

# In-memory cache to ensure speed and prevent rate limits
_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 900  # 15 minutes

WEATHER_CODE_MAP = {
    0: ("Clear sky", "☀️"),
    1: ("Mainly clear", "🌤️"),
    2: ("Partly cloudy", "⛅"),
    3: ("Overcast", "☁️"),
    45: ("Foggy", "🌫️"),
    48: ("Rime fog", "🌫️"),
    51: ("Light drizzle", "🌦️"),
    53: ("Moderate drizzle", "🌦️"),
    55: ("Dense drizzle", "🌧️"),
    61: ("Slight rain", "🌧️"),
    63: ("Moderate rain", "🌧️"),
    65: ("Heavy rain", "🌧️"),
    71: ("Slight snow", "🌨️"),
    73: ("Moderate snow", "🌨️"),
    75: ("Heavy snow", "❄️"),
    80: ("Light showers", "🌦️"),
    81: ("Moderate showers", "🌧️"),
    82: ("Heavy showers", "⛈️"),
    95: ("Thunderstorm", "⛈️"),
    96: ("Thunderstorm with hail", "⛈️"),
    99: ("Heavy thunderstorm", "⛈️"),
}

COUNTRY_CURRENCY_MAP = {
    "India": "INR",
    "France": "EUR",
    "Japan": "JPY",
    "Thailand": "THB",
    "Indonesia": "IDR",
    "Malaysia": "MYR",
    "Singapore": "SGD",
    "United Arab Emirates": "AED",
    "UAE": "AED",
    "United Kingdom": "GBP",
    "UK": "GBP",
    "United States": "USD",
    "USA": "USD",
    "Switzerland": "CHF",
    "Italy": "EUR",
    "Spain": "EUR",
    "Vietnam": "VND",
    "Turkey": "TRY",
    "Egypt": "EGP",
}

def _get_cached(key: str) -> Optional[Any]:
    entry = _CACHE.get(key)
    if entry and (time.time() - entry["time"]) < CACHE_TTL_SECONDS:
        return entry["data"]
    return None

def _set_cached(key: str, data: Any):
    _CACHE[key] = {"time": time.time(), "data": data}

def get_live_weather(lat: float, lon: float, timeout: float = 3.5) -> Dict[str, Any]:
    """
    Fetch live weather data from Open-Meteo for exact destination coordinates.
    Returns current temp, weather condition, icon, humidity, and wind speed.
    """
    cache_key = f"weather_{round(lat, 3)}_{round(lon, 3)}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "SmartAITravelPlanner/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            curr = data.get("current", {})
            w_code = curr.get("weather_code", 0)
            condition_desc, condition_icon = WEATHER_CODE_MAP.get(w_code, ("Fair", "🌤️"))
            result = {
                "success": True,
                "temperature": curr.get("temperature_2m"),
                "unit": "°C",
                "humidity": curr.get("relative_humidity_2m"),
                "wind_speed_kmh": curr.get("wind_speed_10m"),
                "condition": condition_desc,
                "icon": condition_icon,
                "timezone": data.get("timezone", "UTC"),
                "time": curr.get("time"),
            }
            _set_cached(cache_key, result)
            return result
    except Exception as exc:
        fallback = {
            "success": False,
            "error": str(exc),
            "temperature": None,
            "unit": "°C",
            "condition": "Pleasant",
            "icon": "🌤️",
        }
        return fallback

def get_live_wiki_summary(place_name: str, timeout: float = 3.0) -> Dict[str, Any]:
    """
    Fetch live summary, facts and thumbnail photo from Wikipedia REST API.
    """
    clean_name = place_name.split(",")[0].strip()
    cache_key = f"wiki_{clean_name}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    quoted = urllib.parse.quote(clean_name.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{quoted}"
    req = urllib.request.Request(url, headers={"User-Agent": "SmartAITravelPlanner/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            result = {
                "success": True,
                "title": data.get("title", clean_name),
                "extract": data.get("extract", ""),
                "thumbnail": data.get("thumbnail", {}).get("source"),
                "page_url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }
            _set_cached(cache_key, result)
            return result
    except Exception as exc:
        return {"success": False, "error": str(exc), "extract": "", "thumbnail": None, "page_url": ""}

def get_live_currency_rate(country_name: str, timeout: float = 3.0) -> Dict[str, Any]:
    """
    Fetch live foreign exchange conversion from INR to destination currency.
    """
    target_currency = COUNTRY_CURRENCY_MAP.get(country_name, "USD")
    if target_currency == "INR":
        return {"success": True, "base": "INR", "target": "INR", "rate": 1.0, "symbol": "₹"}

    cache_key = f"fx_{target_currency}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = f"https://api.frankfurter.app/latest?from=INR&to={target_currency}"
    req = urllib.request.Request(url, headers={"User-Agent": "SmartAITravelPlanner/2.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            rate = data.get("rates", {}).get(target_currency, 0.0)
            result = {
                "success": True,
                "base": "INR",
                "target": target_currency,
                "rate": rate,
                "symbol": target_currency,
            }
            _set_cached(cache_key, result)
            return result
    except Exception as exc:
        return {"success": False, "error": str(exc), "base": "INR", "target": target_currency, "rate": None}

def get_live_flight_search_url(destination_name: str, start_city: str = "") -> str:
    """
    Generate live Google Flights search deep link with departure and arrival.
    """
    dest_clean = destination_name.split(",")[0].strip()
    origin = start_city.strip() if start_city and start_city.lower() != "not specified" else ""
    if origin:
        query = f"Flights from {origin} to {dest_clean}"
    else:
        query = f"Flights to {dest_clean}"
    return f"https://www.google.com/travel/flights?q={urllib.parse.quote(query)}"

def get_live_hotel_search_url(destination_name: str, hotel_name: str = "") -> str:
    """
    Generate live hotel booking search link.
    """
    dest_clean = destination_name.split(",")[0].strip()
    if hotel_name:
        query = f"{hotel_name} {dest_clean}"
    else:
        query = f"Hotels in {dest_clean}"
    return f"https://www.google.com/travel/hotels?q={urllib.parse.quote(query)}"

def get_live_attraction_map_url(attraction_name: str, destination_name: str) -> str:
    """
    Generate Google Maps navigation search link for an attraction.
    """
    query = f"{attraction_name}, {destination_name}"
    return f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(query)}"

def get_destination_live_feed(dest_dict: Dict[str, Any], start_city: str = "") -> Dict[str, Any]:
    """
    Combine all live APIs for a destination row in the dataset into one rich payload.
    """
    name = dest_dict.get("name", "")
    country = dest_dict.get("country", "")
    lat = float(dest_dict.get("latitude", 0.0))
    lon = float(dest_dict.get("longitude", 0.0))

    weather = get_live_weather(lat, lon)
    wiki = get_live_wiki_summary(name)
    fx = get_live_currency_rate(country)
    flight_url = get_live_flight_search_url(name, start_city)
    hotel_url = get_live_hotel_search_url(name)

    return {
        "destination_id": dest_dict.get("destination_id"),
        "name": name,
        "country": country,
        "coordinates": {"latitude": lat, "longitude": lon},
        "live_weather": weather,
        "live_currency": fx,
        "live_wikipedia": wiki,
        "live_flight_url": flight_url,
        "live_hotel_url": hotel_url,
    }

