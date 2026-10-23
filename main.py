"""Interactive console entry point for Smart AI Travel Planner."""
from pathlib import Path
from travel.data_loader import load_data
from travel.features import validate_request
from travel.model import train_model
from travel.recommender import recommend_destinations
from travel.itinerary import build_itinerary
from travel.map_builder import build_map

ROOT = Path(__file__).resolve().parent

def ask_choice(prompt, choices, default):
    allowed = {x.lower() for x in choices}
    while True:
        value = input(f"{prompt} ({'/'.join(choices)}) [{default}]: ").strip().lower() or default
        if value in allowed:
            return value
        print("Invalid choice. Select one of:", ", ".join(choices))

def ask_int(prompt, default, minimum=1):
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        try:
            value = int(raw) if raw else default
            if value >= minimum:
                return value
        except ValueError:
            pass
        print(f"Enter an integer greater than or equal to {minimum}.")

def ask_float(prompt, default, minimum=1):
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        try:
            value = float(raw) if raw else default
            if value >= minimum:
                return value
        except ValueError:
            pass
        print(f"Enter a number greater than or equal to {minimum}.")

def collect_request():
    print("\nEnter your trip requirements. All prices are illustrative estimates in INR.")
    return validate_request({
        "scope": ask_choice("Trip scope", ["Domestic", "International", "Either"], "Either"),
        "people": ask_int("Number of Travellers", 2),
        "days": ask_int("Trip duration in days", 4),
        "budget": ask_float("Total group budget (INR)", 50000),
        "climate": ask_choice("Preferred climate", ["Any", "Cold", "Mild", "Hot", "Dry", "Tropical"], "Any"),
        "group_type": ask_choice("Group type", ["Solo", "Couple", "Family", "Friends"], "Friends"),
        "interests": input("Interests, comma-separated (e.g. Nature,History,Food) [Nature]: ").strip() or "Nature",
        "start_city": input("Starting city [Not specified]: ").strip() or "Anywhere",
    })

def print_costs(costs):
    print(f"    Estimated total: ₹{costs['total']:,} | transport ₹{costs['transport']:,}, accommodation ₹{costs['accommodation']:,}, food ₹{costs['food']:,}, activities ₹{costs['activities']:,}")
    print(f"    Accommodation assumption: {costs['rooms']} room(s), {costs['nights']} night(s), cheapest listed option: {costs['hotel_name']}")

def main():
    print("=" * 62)
    print("SMART AI TRAVEL PLANNER")
    print("Local dataset • preference ranking • strict budget filtering")
    print("=" * 62)
    frames = load_data()
    model, metrics = train_model()
    print(f"Classifier trained on synthetic profiles; holdout agreement: {metrics['synthetic_holdout_accuracy']:.1%}")
    print("This is not evidence of real-world travel satisfaction.")
    request = collect_request()
    results = recommend_destinations(frames, request, model, limit=5)
    if not results:
        print("\nNo destinations fit the selected scope and total budget.")
        print("Increase the budget, shorten the trip, or change the trip scope.")
        return
    print(f"\nDestinations within ₹{request['budget']:,.0f} group budget:")
    for rank, result in enumerate(results, start=1):
        d = result["destination"]
        print(f"\n{rank}. {d['name']}, {d['country']} — score {result['score']}/100")
        print("    Why:", "; ".join(result["reasons"]))
        print_costs(result["costs"])
    selected_index = ask_int("\nChoose a destination number to generate an itinerary/map", 1, 1)
    selected_index = min(selected_index, len(results)) - 1
    selected = results[selected_index]
    itinerary = build_itinerary(selected["destination"]["destination_id"], frames["attractions"], request["days"])
    print(f"\nITINERARY: {selected['destination']['name']}")
    for day_number, stops in enumerate(itinerary, start=1):
        print(f"\nDay {day_number}")
        if not stops:
            print("  Free time / travel buffer")
        for stop in stops:
            print(f"  - {stop['name']} ({stop['duration_hours']} h, about ₹{stop['estimated_cost_per_person']:,.0f} per person)")
    map_path = ROOT / "artifacts" / "travel_map.html"
    build_map(selected["destination"], itinerary, map_path)
    print(f"\nInteractive map saved to: {map_path}")
    print("Open the HTML file in a browser. Verify prices and travel details independently.")

if __name__ == "__main__":
    main()
