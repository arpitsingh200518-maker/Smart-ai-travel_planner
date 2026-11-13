"""Dynamic trip-cost estimation with live flight pricing from user origin to destination."""
import math
from .flight_api import get_live_flight_quote

def estimate_budget(destination, hotels, request):
    people = int(request["people"])
    days = int(request["days"])
    nights = max(0, days - 1)
    rooms = math.ceil(people / 2)
    options = hotels[hotels["destination_id"].astype(str) == str(destination["destination_id"])]
    if options.empty:
        hotel_rate = float(destination["hotel_price_per_room_night"])
        hotel_name = "Dataset default estimate"
    else:
        cheapest = options.loc[options["price_per_room_night"].astype(float).idxmin()]
        hotel_rate = float(cheapest["price_per_room_night"])
        hotel_name = str(cheapest["hotel_name"])

    # Live Flight Pricing from user's current location or departure city
    origin = request.get("start_city", "")
    flight_quote = get_live_flight_quote(origin, destination)
    flight_price_pp = flight_quote["price_per_person"]
    transport = flight_price_pp * people

    accommodation = hotel_rate * rooms * nights
    food = float(destination["food_per_person_day"]) * people * days
    activities = float(destination["activities_per_person"]) * people
    total = transport + accommodation + food + activities

    return {
        "transport": round(transport),
        "flight_per_person": round(flight_price_pp),
        "flight_origin": flight_quote["origin_city"],
        "flight_distance_km": flight_quote["distance_km"],
        "flight_duration": flight_quote["duration_str"],
        "flight_search_url": flight_quote["search_url"],
        "accommodation": round(accommodation),
        "food": round(food),
        "activities": round(activities),
        "total": round(total),
        "rooms": rooms,
        "nights": nights,
        "hotel_name": hotel_name,
    }
