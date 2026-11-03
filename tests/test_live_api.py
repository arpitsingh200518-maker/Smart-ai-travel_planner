"""Unit tests for Live API integration and REST API endpoints."""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from travel.live_api import (
    get_live_weather,
    get_live_wiki_summary,
    get_live_currency_rate,
    get_live_flight_search_url,
    get_live_hotel_search_url,
    get_destination_live_feed,
)

class LiveAPITests(unittest.TestCase):
    def test_flight_search_url_generation(self):
        url = get_live_flight_search_url("Paris", "Delhi")
        self.assertIn("google.com/travel/flights", url)
        self.assertIn("Paris", url)

    def test_hotel_search_url_generation(self):
        url = get_live_hotel_search_url("Goa", "Goa Budget Stay")
        self.assertIn("google.com/travel/hotels", url)
        self.assertIn("Goa", url)

    def test_currency_conversion_domestic(self):
        fx = get_live_currency_rate("India")
        self.assertTrue(fx["success"])
        self.assertEqual(fx["target"], "INR")
        self.assertEqual(fx["rate"], 1.0)

    def test_live_weather_returns_expected_structure(self):
        # Coordinates for Goa
        w = get_live_weather(15.2993, 74.1240)
        self.assertIn("condition", w)
        self.assertIn("unit", w)
        self.assertEqual(w["unit"], "°C")

    def test_destination_live_feed(self):
        dest = {
            "destination_id": "IN01",
            "name": "Goa",
            "country": "India",
            "latitude": 15.2993,
            "longitude": 74.1240,
        }
        feed = get_destination_live_feed(dest, start_city="Mumbai")
        self.assertEqual(feed["destination_id"], "IN01")
        self.assertIn("live_weather", feed)
        self.assertIn("live_flight_url", feed)
        self.assertIn("live_hotel_url", feed)
        self.assertIn("live_currency", feed)

if __name__ == "__main__":
    unittest.main()

