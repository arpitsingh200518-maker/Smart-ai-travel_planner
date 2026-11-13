"""Unit tests for live flight pricing API, dynamic budget estimation, and CSV validation."""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from travel.data_loader import load_data
from travel.budget import estimate_budget
from travel.flight_api import (
    get_current_location,
    resolve_location,
    haversine_distance_km,
    calculate_flight_fare,
    get_live_flight_quote,
)

class FlightAPITests(unittest.TestCase):
    def setUp(self):
        self.frames = load_data()

    def test_destinations_csv_has_no_transport_per_person_column(self):
        destinations = self.frames["destinations"]
        self.assertNotIn("transport_per_person", destinations.columns)

    def test_current_location_detection(self):
        loc = get_current_location()
        self.assertIn("city", loc)
        self.assertIn("latitude", loc)
        self.assertIn("longitude", loc)
        self.assertIsInstance(loc["latitude"], float)

    def test_resolve_location_common_and_custom(self):
        lat, lon, city, country = resolve_location("Mumbai")
        self.assertAlmostEqual(lat, 19.0760, places=2)
        self.assertEqual(city, "Mumbai")

        lat_d, lon_d, city_d, country_d = resolve_location("Delhi")
        self.assertAlmostEqual(lat_d, 28.6139, places=2)

    def test_haversine_distance(self):
        # Delhi to Mumbai distance is ~1150 km
        dist = haversine_distance_km(28.6139, 77.2090, 19.0760, 72.8777)
        self.assertGreater(dist, 1000)
        self.assertLess(dist, 1300)

    def test_calculate_flight_fare_pricing(self):
        price, duration = calculate_flight_fare(1150, is_international=False)
        self.assertGreater(price, 2000)
        self.assertIn("h", duration)

    def test_live_flight_quote(self):
        dest = self.frames["destinations"].iloc[0].to_dict()  # Goa
        quote = get_live_flight_quote("Delhi", dest)
        self.assertGreater(quote["price_per_person"], 0)
        self.assertEqual(quote["origin_city"], "Delhi")
        self.assertIn("google.com/travel/flights", quote["search_url"])

    def test_estimate_budget_uses_live_flight_pricing(self):
        dest = self.frames["destinations"].iloc[0].to_dict()
        req_mumbai = {
            "people": 2, "days": 3, "budget": 50000,
            "scope": "domestic", "start_city": "Mumbai",
        }
        costs_mumbai = estimate_budget(dest, self.frames["hotels"], req_mumbai)
        
        req_delhi = {
            "people": 2, "days": 3, "budget": 50000,
            "scope": "domestic", "start_city": "Delhi",
        }
        costs_delhi = estimate_budget(dest, self.frames["hotels"], req_delhi)

        # Flights from Delhi to Goa are farther than Mumbai to Goa, so transport must differ
        self.assertGreater(costs_delhi["transport"], costs_mumbai["transport"])
        self.assertEqual(costs_delhi["total"], costs_delhi["transport"] + costs_delhi["accommodation"] + costs_delhi["food"] + costs_delhi["activities"])

if __name__ == "__main__":
    unittest.main()

