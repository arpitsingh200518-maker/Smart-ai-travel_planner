"""Illustrative trip-cost estimation; values are not live quotes."""
import math

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
    transport = float(destination["transport_per_person"]) * people
    accommodation = hotel_rate * rooms * nights
    food = float(destination["food_per_person_day"]) * people * days
    activities = float(destination["activities_per_person"]) * people
    total = transport + accommodation + food + activities
    return {
        "transport": round(transport), "accommodation": round(accommodation),
        "food": round(food), "activities": round(activities), "total": round(total),
        "rooms": rooms, "nights": nights, "hotel_name": hotel_name,
    }
