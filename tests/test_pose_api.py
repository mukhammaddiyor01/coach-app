"""Exercise the local frame endpoint without using real camera data."""
import unittest

from fastapi.testclient import TestClient

from backend.main import app
from backend.vision.pose_detector import (
    InvalidFrameError,
    ModelUnavailableError,
    PoseBusyError,
    PoseDetectionError,
    get_pose_detector,
)


class FakeDetector:
    def __init__(self):
        self.calls = 0
        self.error = None
        self.landmarks = []

    def detect(self, frame_bytes):
        self.calls += 1
        if self.error:
            raise self.error
        return {"landmarks": self.landmarks, "width": 640, "height": 360}


class PoseApiTests(unittest.TestCase):
    def setUp(self):
        self.detector = FakeDetector()
        app.dependency_overrides[get_pose_detector] = lambda: self.detector
        self.addCleanup(app.dependency_overrides.clear)
        self.client = TestClient(app, base_url="http://127.0.0.1")
        self.addCleanup(self.client.close)
        self.headers = {
            "content-type": "image/jpeg",
            "x-coach-camera": "1",
            "origin": "http://127.0.0.1",
        }

    def test_frame_returns_only_landmarks_and_dimensions_without_cache(self):
        point = {"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 0.9, "presence": 0.9}
        self.detector.landmarks = [point] * 33
        response = self.client.post("/api/pose", content=b"dummy-frame", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["landmarks"]), 33)
        self.assertEqual(set(response.json()), {"landmarks", "width", "height"})
        self.assertNotIn("dummy-frame", response.text)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_no_body_is_a_normal_empty_result(self):
        response = self.client.post("/api/pose", content=b"frame", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["landmarks"], [])

    def test_cross_origin_frames_are_rejected_before_detection(self):
        self.headers["origin"] = "https://untrusted.example"
        response = self.client.post("/api/pose", content=b"frame", headers=self.headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.detector.calls, 0)

    def test_missing_camera_header_is_rejected(self):
        del self.headers["x-coach-camera"]
        response = self.client.post("/api/pose", content=b"frame", headers=self.headers)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.detector.calls, 0)

    def test_cross_origin_preflight_does_not_grant_access(self):
        response = self.client.options("/api/pose", headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-Coach-Camera",
        })
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    def test_other_content_types_are_rejected(self):
        self.headers["content-type"] = "text/plain"
        response = self.client.post("/api/pose", content=b"frame", headers=self.headers)
        self.assertEqual(response.status_code, 415)
        self.assertEqual(self.detector.calls, 0)

    def test_large_body_is_rejected_without_detection(self):
        response = self.client.post("/api/pose", content=b"x" * 1_000_001, headers=self.headers)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.detector.calls, 0)

    def test_streamed_body_cannot_bypass_size_limit(self):
        chunks = (b"x" * 600_000 for _ in range(2))
        response = self.client.post("/api/pose", content=chunks, headers=self.headers)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(self.detector.calls, 0)

    def test_model_errors_are_translated_to_safe_http_responses(self):
        errors = [
            (InvalidFrameError("Invalid JPEG frame."), 400),
            (ModelUnavailableError("Run python download_model.py."), 503),
            (PoseBusyError("busy"), 429),
            (PoseDetectionError("internal failure"), 503),
        ]
        for error, expected_status in errors:
            with self.subTest(error=type(error).__name__):
                self.detector.error = error
                response = self.client.post("/api/pose", content=b"frame", headers=self.headers)
                self.assertEqual(response.status_code, expected_status)
                self.assertEqual(response.headers["Cache-Control"], "no-store")
                self.assertNotIn("internal failure", response.text)


if __name__ == "__main__":
    unittest.main()
