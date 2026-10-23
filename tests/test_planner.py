"""Unit tests for budget, validation, recommendation, and itinerary constraints."""
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from travel.data_loader import load_data
from travel.features import validate_request
from travel.model import train_model
from travel.budget import estimate_budget
from travel.recommender import recommend_destinations
from travel.itinerary import build_itinerary

class PlannerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = load_data()
        cls.model, cls.metrics = train_model()

    def request(self, **updates):
        request = {
            "scope": "either", "people": 2, "days": 3, "budget": 100000,
            "climate": "any", "group_type": "friends",
            "interests": ["nature", "food"], "start_city": "Prayagraj",
        }
        request.update(updates)
        return validate_request(request)

    def test_loads_twenty_destinations(self):
        self.assertEqual(len(self.frames["destinations"]), 20)

    def test_invalid_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_request({"people": 2, "days": 3, "budget": 0})

    def test_invalid_people_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_request({"people": 0, "days": 3, "budget": 10000})

    def test_estimated_budget_has_expected_components(self):
        destination = self.frames["destinations"].iloc[0].to_dict()
        costs = estimate_budget(destination, self.frames["hotels"], self.request())
        self.assertEqual(costs["total"], costs["transport"] + costs["accommodation"] + costs["food"] + costs["activities"])
        self.assertGreater(costs["total"], 0)

    def test_recommendations_never_exceed_budget(self):
        request = self.request(budget=50000)
        results = recommend_destinations(self.frames, request, self.model)
        self.assertTrue(all(item["costs"]["total"] <= request["budget"] for item in results))

    def test_domestic_scope_excludes_international(self):
        results = recommend_destinations(self.frames, self.request(scope="domestic"), self.model)
        self.assertTrue(all(item["destination"]["scope"] == "domestic" for item in results))

    def test_tiny_budget_can_return_no_results(self):
        results = recommend_destinations(self.frames, self.request(budget=1), self.model)
        self.assertEqual(results, [])

    def test_itinerary_respects_daily_cap(self):
        destination_id = self.frames["destinations"].iloc[0]["destination_id"]
        itinerary = build_itinerary(destination_id, self.frames["attractions"], days=3, daily_cap=7.0)
        for day in itinerary:
            self.assertLessEqual(sum(stop["duration_hours"] for stop in day), 7.0)

    def test_model_metrics_are_valid(self):
        self.assertGreaterEqual(self.metrics["synthetic_holdout_accuracy"], 0.0)
        self.assertLessEqual(self.metrics["synthetic_holdout_accuracy"], 1.0)

if __name__ == "__main__":
    unittest.main()
