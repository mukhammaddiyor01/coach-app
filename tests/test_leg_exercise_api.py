"""Exercise-specific sessions must select the matching service and remain isolated."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.vision.pose_detector import get_pose_detector
from backend.workout_sessions import WorkoutSessions, get_workout_sessions
from test_squats_service import squat_body
from test_lunge_service import lunge_body


class FakeDetector:
    landmarks = []
    calls = 0

    def detect(self, frame):
        self.calls += 1
        return {"landmarks": [dict(point, z=0) for point in self.landmarks], "width": 640, "height": 480}


class LegExerciseApiTests(unittest.TestCase):
    def setUp(self):
        self.detector = FakeDetector()
        self.sessions = WorkoutSessions()
        app.dependency_overrides[get_pose_detector] = lambda: self.detector
        app.dependency_overrides[get_workout_sessions] = lambda: self.sessions
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app, base_url="http://127.0.0.1")
        self.addCleanup(self.client.close)
        self.headers = {"X-Coach-Camera": "1", "Origin": "http://127.0.0.1"}

    def create(self, exercise):
        response = self.client.post(f"/api/{exercise}/session", headers=self.headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["exercise_id"], exercise)
        self.assertEqual(response.json()["workout"]["rep_count"], 0)
        return response.json()["session_id"]

    def frame(self, exercise, token, content=b"synthetic-frame", **headers):
        return self.client.post(f"/api/{exercise}/frame", content=content, headers={
            **self.headers, "Content-Type": "image/jpeg", "X-Coach-Session": token, **headers,
        })

    def test_each_leg_service_counts_a_full_rep_via_http(self):
        for exercise, make_body, angle in (("squats", squat_body, "knee_angle"), ("lunge", lunge_body, "left_knee_angle")):
            with self.subTest(exercise=exercise):
                token, other = self.create(exercise), self.create(exercise)
                with patch("backend.workout_sessions.monotonic", side_effect=[0, 0.2, 0.4, 0.6, 0.8, 1, 1.2]):
                    for position in ("up", "up", "down", "down", "up", "up"):
                        self.detector.landmarks = make_body(position)
                        response = self.frame(exercise, token)
                        self.assertEqual(response.status_code, 200)
                    result = response.json()["workout"]
                    self.assertEqual(result["rep_count"], 1)
                    self.assertIsNotNone(result[angle])
                    self.assertIsNone(result["elbow_angle"])
                    self.assertEqual(self.frame(exercise, other).json()["workout"]["rep_count"], 0)

    def test_session_cannot_be_used_or_deleted_through_another_exercise(self):
        token = self.create("squats")
        self.assertEqual(self.frame("lunge", token).status_code, 404)
        self.assertEqual(self.frame("pushup", token).status_code, 404)
        response = self.client.delete("/api/lunge/session", headers={**self.headers, "X-Coach-Session": token})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.detector.calls, 0)
        self.assertEqual(self.frame("squats", token).status_code, 200)

    def test_unknown_exercise_is_rejected_without_creating_state(self):
        self.assertEqual(self.client.post("/api/unknown/session", headers=self.headers).status_code, 404)
        self.assertEqual(self.sessions.sessions, {})
        from backend.workout_sessions import UnsupportedExerciseError
        with self.assertRaises(UnsupportedExerciseError):
            self.sessions.create("unknown")

    def test_privacy_and_frame_guards_apply_to_both_new_exercises(self):
        for exercise in ("squats", "lunge"):
            token = self.create(exercise)
            for method, suffix in (("POST", "session"), ("DELETE", "session"), ("POST", "frame")):
                url = f"/api/{exercise}/{suffix}"
                for headers in ({}, {**self.headers, "Origin": "https://untrusted.example"}):
                    self.assertEqual(self.client.request(method, url, headers=headers).status_code, 403)
            self.assertEqual(self.frame(exercise, token, b"x" * 1_000_001).status_code, 413)
            response = self.client.post(f"/api/{exercise}/frame", content=b"x", headers={**self.headers, "X-Coach-Session": token})
            self.assertEqual(response.status_code, 415)
        self.assertEqual(self.detector.calls, 0)

    def test_no_body_is_waiting_and_reset_uses_fresh_state(self):
        for exercise in ("squats", "lunge"):
            token = self.create(exercise)
            response = self.frame(exercise, token)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["workout"]["status"], "waiting")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            closed = self.client.delete(f"/api/{exercise}/session", headers={**self.headers, "X-Coach-Session": token})
            self.assertEqual(closed.status_code, 204)
            self.assertEqual(self.frame(exercise, token).status_code, 404)
            self.assertNotEqual(self.create(exercise), token)


if __name__ == "__main__":
    unittest.main()
