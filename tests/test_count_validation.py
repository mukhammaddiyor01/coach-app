"""Manual trial comparisons do not infer camera accuracy or change exercise state."""
import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.count_validation import InvalidCountCheckError, compare_counts


class CountValidationTests(unittest.TestCase):
    def test_match_extra_and_missed_counts(self):
        for manual, observed, outcome, difference in ((5, 5, "match", 0), (5, 7, "extra", 2), (5, 3, "missed", -2), (0, 0, "match", 0)):
            with self.subTest(outcome=outcome):
                result = compare_counts(manual, observed)
                self.assertEqual(result["outcome"], outcome)
                self.assertEqual(result["difference"], difference)
                self.assertEqual(result["manual_count"], manual)
                self.assertEqual(result["observed_count"], observed)
                self.assertNotIn("accuracy", result)

    def test_counts_must_be_bounded_integers(self):
        for invalid in (-1, 1001, True, "5", 1.5, None, float("nan")):
            for values in ((invalid, 0), (0, invalid)):
                with self.subTest(values=values):
                    with self.assertRaises(InvalidCountCheckError):
                        compare_counts(*values)


class CountValidationApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url="http://127.0.0.1")
        self.addCleanup(self.client.close)
        self.headers = {"X-Coach-Camera": "1", "Origin": "http://127.0.0.1"}

    def test_each_exercise_compares_counts_and_does_not_cache_results(self):
        for exercise in ("pushup", "squats", "lunge"):
            response = self.client.post(f"/api/{exercise}/count-check", headers=self.headers, json={"manual_count": 5, "observed_count": 4})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["exercise_id"], exercise)
            self.assertEqual(response.json()["difference"], -1)
            self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_foreign_origin_missing_header_and_unknown_exercise_are_rejected(self):
        counts = {"manual_count": 5, "observed_count": 5}
        self.assertEqual(self.client.post("/api/pushup/count-check", json=counts).status_code, 403)
        response = self.client.post("/api/pushup/count-check", json=counts, headers={**self.headers, "Origin": "https://untrusted.example"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.post("/api/unknown/count-check", json=counts, headers=self.headers).status_code, 404)

    def test_malformed_counts_and_extra_fields_are_rejected(self):
        for counts in ({"manual_count": True, "observed_count": 1}, {"manual_count": 1, "observed_count": -1}, {"manual_count": 1, "observed_count": 1, "frame": "not-accepted"}):
            self.assertEqual(self.client.post("/api/pushup/count-check", json=counts, headers=self.headers).status_code, 422)


if __name__ == "__main__":
    unittest.main()
