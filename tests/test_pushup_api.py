"""HTTP integration uses synthetic landmarks; no camera capture is needed."""
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.vision.pose_detector import PoseBusyError, get_pose_detector
from backend.workout_sessions import WorkoutSessions, get_workout_sessions
from test_pushup_service import body


class FakeDetector:
    def __init__(self):
        self.landmarks = []
        self.calls = 0
        self.error = None

    def detect(self, frame):
        self.calls += 1
        if self.error:
            raise self.error
        points = [dict(point, z=0) for point in self.landmarks]
        return {"landmarks": points, "width": 640, "height": 480}


class PushUpApiTests(unittest.TestCase):
    def setUp(self):
        self.detector = FakeDetector()
        self.sessions = WorkoutSessions()
        app.dependency_overrides[get_pose_detector] = lambda: self.detector
        app.dependency_overrides[get_workout_sessions] = lambda: self.sessions
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app, base_url="http://127.0.0.1")
        self.addCleanup(self.client.close)
        self.headers = {"x-coach-camera": "1", "origin": "http://127.0.0.1"}

    def create(self):
        response = self.client.post("/api/pushup/session", headers=self.headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["workout"]["rep_count"], 0)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        return response.json()["session_id"]

    def frame(self, token):
        return self.client.post("/api/pushup/frame", content=b"synthetic-frame", headers={
            **self.headers, "x-coach-session": token, "content-type": "image/jpeg",
        })

    def test_full_repetition_flows_through_api_and_other_session_stays_zero(self):
        token, other_token = self.create(), self.create()
        with patch("backend.workout_sessions.monotonic", side_effect=[0, 0.2, 0.4, 0.6, 0.8, 1, 1.2]):
            for position in ("up", "up", "down", "down", "up", "up"):
                self.detector.landmarks = body(position)
                response = self.frame(token)
                self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["workout"]["rep_count"], 1)
            self.assertNotIn(token, response.text)
            self.assertEqual(self.frame(other_token).json()["workout"]["rep_count"], 0)

    def test_missing_body_returns_waiting_state(self):
        response = self.frame(self.create())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["workout"]["status"], "waiting")

    def test_closed_session_rejects_frames_and_new_session_starts_at_zero(self):
        token = self.create()
        response = self.client.delete("/api/pushup/session", headers={**self.headers, "x-coach-session": token})
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.frame(token).status_code, 404)
        self.assertEqual(self.detector.calls, 0)
        self.assertNotEqual(self.create(), token)

    def test_camera_origin_and_header_checks_apply_to_every_endpoint(self):
        token = self.create()
        for method, path in (("POST", "/api/pushup/session"), ("DELETE", "/api/pushup/session"), ("POST", "/api/pushup/frame")):
            for headers in ({}, {**self.headers, "origin": "https://untrusted.example"}):
                with self.subTest(method=method, path=path):
                    response = self.client.request(method, path, headers={**headers, "x-coach-session": token})
                    self.assertEqual(response.status_code, 403)
        self.assertEqual(len(self.sessions.sessions), 1)
        self.assertEqual(self.detector.calls, 0)

    def test_frame_size_and_type_guards_apply_before_inference(self):
        token = self.create()
        headers = {**self.headers, "x-coach-session": token}
        response = self.client.post("/api/pushup/frame", content=b"frame", headers=headers)
        self.assertEqual(response.status_code, 415)
        headers["content-type"] = "image/jpeg"
        response = self.client.post("/api/pushup/frame", content=b"x" * 1_000_001, headers=headers)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.detector.calls, 0)

    def test_unknown_or_malformed_session_is_rejected(self):
        for token in ("", "invalid", "0" * 32):
            self.assertEqual(self.frame(token).status_code, 404)
        self.assertEqual(self.detector.calls, 0)

    def test_capacity_and_adapter_errors_are_safe(self):
        from backend.workout_sessions import MAX_SESSIONS
        token = self.create()
        for _ in range(MAX_SESSIONS - 1):
            self.sessions.create()
        self.assertEqual(self.client.post("/api/pushup/session", headers=self.headers).status_code, 429)
        self.detector.error = PoseBusyError("private internal detail")
        response = self.frame(token)
        self.assertEqual(response.status_code, 429)
        self.assertNotIn("private internal detail", response.text)
        self.assertEqual(response.headers["Retry-After"], "1")

    def test_invalid_landmarks_return_safe_failure_without_leaking_data(self):
        token = self.create()
        self.detector.landmarks = body()
        self.detector.landmarks[11]["x"] = float("nan")
        response = self.frame(token)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("nan", response.text)

    def test_each_page_loads_matching_counting_controls(self):
        for exercise, angle in (("pushup", "elbow-angle"), ("squats", "knee-angle"), ("lunge", "left-knee-angle")):
            with self.subTest(exercise=exercise):
                response = self.client.get("/workout/" + exercise + "/camera")
                self.assertEqual(response.status_code, 200)
                self.assertIn('data-exercise="' + exercise + '"', response.text)
                self.assertIn('id="rep-count"', response.text)
                self.assertIn('id="reset-count"', response.text)
                self.assertIn('id="' + angle + '"', response.text)
                self.assertLess(response.text.index("js/workout.js"), response.text.index("js/pose.js"))
                self.assertLess(response.text.index("js/pose.js"), response.text.index("js/camera.js"))
                if exercise != "pushup":
                    self.assertNotIn('id="elbow-angle"', response.text)
                if exercise == "lunge":
                    self.assertIn('id="right-knee-angle"', response.text)
        self.assertEqual(self.client.get("/static/js/workout.js").status_code, 200)

    def test_application_shutdown_clears_temporary_sessions(self):
        from backend.workout_sessions import workout_sessions
        with TestClient(app, base_url="http://127.0.0.1"):
            workout_sessions.create()
        self.assertEqual(workout_sessions.sessions, {})


if __name__ == "__main__":
    unittest.main()
