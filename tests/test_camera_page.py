"""Check navigation, accessible controls, and the single on-camera counter."""
from html.parser import HTMLParser
import unittest

from fastapi.testclient import TestClient

from backend.main import app


class PageElements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.elements = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        identifier = attributes.get("id")
        if identifier:
            self.elements.setdefault(identifier, []).append((attributes, tuple(self.stack)))
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(identifier or tag)

    def handle_endtag(self, tag):
        if self.stack:
            self.stack.pop()


class CameraPageTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url="http://127.0.0.1")
        self.addCleanup(self.client.close)

    def test_preparation_links_to_selected_camera_without_camera_scripts(self):
        for exercise in ("pushup", "squats", "lunge"):
            response = self.client.get(f"/workout/{exercise}")
            page = PageElements()
            page.feed(response.text)
            attributes, _ = page.elements["start-workout"][0]
            self.assertEqual(attributes["href"], f"http://127.0.0.1/workout/{exercise}/camera")
            self.assertNotIn("rep-count", page.elements)
            self.assertNotIn("js/camera.js", response.text)

    def test_count_and_guidance_live_inside_camera_frame_even_before_start(self):
        for exercise in ("pushup", "squats", "lunge"):
            response = self.client.get(f"/workout/{exercise}/camera")
            self.assertEqual(response.status_code, 200)
            page = PageElements()
            page.feed(response.text)
            for identifier in ("rep-count", "rep-phase", "workout-message"):
                self.assertEqual(len(page.elements[identifier]), 1)
                _, ancestors = page.elements[identifier][0]
                self.assertIn("camera-screen", ancestors)
                self.assertNotIn("camera-stage", ancestors)
            attributes, _ = page.elements["workout-results"][0]
            self.assertEqual(attributes["data-exercise"], exercise)
            self.assertIn("hidden", page.elements["camera-video"][0][0])
            self.assertIn("hidden", page.elements["camera-stage"][0][0])
            self.assertIn("playsinline", page.elements["camera-video"][0][0])
            for identifier in ("start-camera", "stop-camera", "reset-count", "camera-facing"):
                self.assertEqual(len(page.elements[identifier]), 1)
            self.assertIn('class="live-workout-page"', response.text)
            self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_start_guidance_matches_each_exercise(self):
        for exercise in ("pushup", "lunge"):
            response = self.client.get(f"/workout/{exercise}/camera")
            self.assertIn("Your starting position is detected automatically.", response.text)
            self.assertNotIn("hold the upper position", response.text)
        response = self.client.get("/workout/squats/camera")
        self.assertIn("then begin standing", response.text)

    def test_unknown_exercise_has_no_camera_scripts_or_count(self):
        response = self.client.get("/workout/unknown/camera")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("js/camera.js", response.text)
        self.assertNotIn('id="rep-count"', response.text)


if __name__ == "__main__":
    unittest.main()
