"""Dynamic trip-cost estimation using local CSV market prices."""
import math
import urllib.parse

def estimate_budget(destination, hotels, request, flights=None):
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

    origin_city = str(request.get("start_city", "")).strip() or "Delhi"
    dest_id = str(destination["destination_id"])

    # Lookup real flight prices from flights dataset if available
    flight_found = False
    flight_airlines = ""
    if flights is not None and not flights.empty:
        match = flights[(flights["origin_city"].str.lower() == origin_city.lower()) & (flights["destination_id"] == dest_id)]
        if not match.empty:
            row = match.iloc[0]
            flight_min_pp = int(row["flight_price_min"])
            flight_max_pp = int(row["flight_price_max"])
            flight_duration = str(row["flight_duration"])
            flight_airlines = str(row.get("airline", ""))
            flight_found = True

    if not flight_found:
        flight_min_pp = int(float(destination.get("flight_price_min", destination.get("transport_per_person", 3500))))
        flight_max_pp = int(float(destination.get("flight_price_max", round(flight_min_pp * 2.5 / 100) * 100)))
        flight_duration = str(destination.get("flight_duration", "2h 15m"))

    transport_min = flight_min_pp * people
    transport_max = flight_max_pp * people
    transport = transport_min

    accommodation = hotel_rate * rooms * nights
    food = float(destination["food_per_person_day"]) * people * days
    activities = float(destination["activities_per_person"]) * people

    total_min = int(round(transport_min + accommodation + food + activities))
    total_max = int(round(transport_max + accommodation + food + activities))
    total = total_min

    return {
        "transport": int(round(transport)),
        "transport_min": int(round(transport_min)),
        "transport_max": int(round(transport_max)),
        "transport_range_str": f"₹{int(round(transport_min)):,} - ₹{int(round(transport_max)):,}",
        "flight_min": flight_min_pp,
        "flight_max": flight_max_pp,
        "flight_per_person": flight_min_pp,
        "flight_range_str": f"₹{flight_min_pp:,} - ₹{flight_max_pp:,}",
        "flight_origin": origin_city,
        "flight_distance_km": 0,
        "flight_duration": flight_duration,
        "flight_airlines": flight_airlines,
        "accommodation": int(round(accommodation)),
        "food": int(round(food)),
        "activities": int(round(activities)),
        "total": total,
        "total_min": total_min,
        "total_max": total_max,
        "total_range_str": f"₹{total_min:,} - ₹{total_max:,}",
        "rooms": rooms,
        "nights": nights,
        "hotel_name": hotel_name,
    }
