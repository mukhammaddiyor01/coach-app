"""Feedback passes through HTTP without treating missing joints as correct form."""
import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.vision.pose_detector import get_pose_detector
from backend.workout_sessions import WorkoutSessions, get_workout_sessions
from test_pushup_service import body
from test_squats_service import squat_body
from test_lunge_service import lunge_body


class FeedbackApiTests(unittest.TestCase):
    def setUp(self):
        self.landmarks = []
        self.sessions = WorkoutSessions()
        app.dependency_overrides[get_workout_sessions] = lambda: self.sessions

        class Detector:
            def detect(detector, frame):
                return {"landmarks": [dict(point, z=0) for point in self.landmarks], "width": 640, "height": 480}

        app.dependency_overrides[get_pose_detector] = Detector
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app, base_url="http://127.0.0.1")
        self.addCleanup(self.client.close)
        self.headers = {"X-Coach-Camera": "1"}

    def frame(self, exercise):
        session = self.client.post(f"/api/{exercise}/session", headers=self.headers).json()
        self.assertEqual(session["workout"]["feedback"]["level"], "unavailable")
        return self.client.post(f"/api/{exercise}/frame", content=b"frame", headers={
            **self.headers, "Content-Type": "image/jpeg", "X-Coach-Session": session["session_id"],
        })

    def test_each_exercise_returns_observed_feedback_and_missing_body_clears_it(self):
        for exercise, make_body in (("pushup", body), ("squats", squat_body), ("lunge", lunge_body)):
            self.landmarks = make_body()
            response = self.frame(exercise)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["workout"]["feedback"]["level"], "observed")
            self.landmarks = []
            self.assertEqual(self.frame(exercise).json()["workout"]["feedback"]["level"], "unavailable")

    def test_specific_correction_survives_response_validation(self):
        self.landmarks = body()
        self.landmarks[25]["y"] = 220 / 480
        result = self.frame("pushup").json()["workout"]
        self.assertEqual(result["feedback"]["code"], "knees_bent")
        self.assertEqual(result["feedback"]["level"], "adjust")
        self.assertEqual(result["rep_count"], 0)


if __name__ == "__main__":
    unittest.main()
