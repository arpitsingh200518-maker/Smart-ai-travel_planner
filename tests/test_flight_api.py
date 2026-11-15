"""Unit tests for CSV market pricing, offline budget estimation, and CSV validation."""
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

    def test_destinations_csv_has_market_flight_columns(self):
        destinations = self.frames["destinations"]
        self.assertIn("flight_price_min", destinations.columns)
        self.assertIn("flight_price_max", destinations.columns)
        self.assertIn("flight_duration", destinations.columns)
        self.assertIn("transport_per_person", destinations.columns)
        # Verify values are positive numbers
        self.assertTrue(all(destinations["flight_price_min"] > 0))
        self.assertTrue(all(destinations["flight_price_max"] > destinations["flight_price_min"]))

    def test_current_location_offline(self):
        loc = get_current_location()
        self.assertIn("city", loc)
        self.assertIn("latitude", loc)
        self.assertIn("longitude", loc)
        self.assertIsInstance(loc["latitude"], float)

    def test_resolve_location_offline(self):
        lat, lon, city, country = resolve_location("Mumbai")
        self.assertAlmostEqual(lat, 19.0760, places=2)
        self.assertEqual(city, "Mumbai")

        lat_d, lon_d, city_d, country_d = resolve_location("Delhi")
        self.assertAlmostEqual(lat_d, 28.6139, places=2)

    def test_haversine_distance(self):
        dist = haversine_distance_km(28.6139, 77.2090, 19.0760, 72.8777)
        self.assertGreater(dist, 1000)
        self.assertLess(dist, 1300)

    def test_calculate_flight_fare_pricing(self):
        fare = calculate_flight_fare(1150, is_international=False)
        self.assertGreater(fare.price_min, 2000)
        self.assertGreater(fare.price_max, fare.price_min)
        self.assertIn("h", fare.duration_str)

    def test_flight_quote_from_csv(self):
        dest = self.frames["destinations"].iloc[0].to_dict()  # Goa
        quote = get_live_flight_quote("Delhi", dest)
        self.assertEqual(quote["price_min"], dest["flight_price_min"])
        self.assertEqual(quote["price_max"], dest["flight_price_max"])
        self.assertIn("-", quote["price_range_str"])
        self.assertEqual(quote["origin_city"], "Delhi")
        self.assertIn("google.com/travel/flights", quote["search_url"])

    def test_estimate_budget_uses_csv_market_pricing(self):
        dest = self.frames["destinations"].iloc[0].to_dict()
        req = {
            "people": 2, "days": 3, "budget": 50000,
            "scope": "domestic", "start_city": "Delhi",
        }
        costs = estimate_budget(dest, self.frames["hotels"], req)
        expected_transport = dest["flight_price_min"] * 2
        self.assertEqual(costs["transport"], expected_transport)
        self.assertIn("-", costs["transport_range_str"])
        self.assertIn("-", costs["flight_range_str"])
        self.assertIn("-", costs["total_range_str"])
        self.assertGreater(costs["total_max"], costs["total_min"])
        self.assertEqual(costs["total"], costs["transport"] + costs["accommodation"] + costs["food"] + costs["activities"])

if __name__ == "__main__":
    unittest.main()
