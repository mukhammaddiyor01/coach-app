"""Verify HTTP privacy boundaries without a network server or real credentials."""
from pathlib import Path
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.main import app
from backend.security import PublicStaticFiles, SECURITY_HEADERS


class HttpPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, base_url="http://127.0.0.1")
        self.addCleanup(self.client.close)

    def test_pages_assets_and_errors_include_privacy_headers(self):
        paths = ["/", "/workout/pushup", "/workout/unknown", "/static/js/camera.js"]

        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                for name, value in SECURITY_HEADERS.items():
                    self.assertEqual(response.headers.get(name), value)

    def test_foreign_host_is_rejected_without_rendering_app(self):
        response = self.client.get("/", headers={"host": "untrusted.example"})
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("Choose your exercise", response.text)
        self.assertEqual(response.headers["Cache-Control"], "no-store")

    def test_localhost_and_loopback_are_accepted(self):
        for host in ("localhost:8000", "127.0.0.1:8000"):
            with self.subTest(host=host):
                response = self.client.get("/", headers={"host": host})
                self.assertEqual(response.status_code, 200)

    def test_project_files_are_not_available_as_http_routes(self):
        paths = ["/.env", "/.git/config", "/backend/main.py", "/AGENTS.md", "/requirements.txt"]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_debug_and_documentation_are_disabled(self):
        self.assertFalse(app.debug)
        for path in ("/docs", "/redoc", "/openapi.json"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_all_exercise_pages_still_load_with_camera_controls(self):
        for exercise in ("pushup", "squats", "lunge"):
            with self.subTest(exercise=exercise):
                response = self.client.get(f"/workout/{exercise}")
                self.assertEqual(response.status_code, 200)
                self.assertIn('id="start-camera"', response.text)

    def test_browser_policy_blocks_external_connections_and_unneeded_devices(self):
        response = self.client.get("/")
        policy = response.headers["Content-Security-Policy"]
        self.assertIn("connect-src 'self'", policy)
        self.assertIn("script-src 'self'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertIn("microphone=()", response.headers["Permissions-Policy"])
        self.assertIn("camera=(self)", response.headers["Permissions-Policy"])


class StaticFilePrivacyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        static_app = FastAPI()
        static_app.mount("/static", PublicStaticFiles(directory=self.root), name="static")
        self.client = TestClient(static_app)
        self.addCleanup(self.client.close)

    def test_misplaced_private_files_cannot_be_downloaded(self):
        private_files = [
            ".env", ".env.local", "private.key", "certificate.pem", "session.mp4",
            "users.sqlite3", "app.log", "model.task", "app.js.map", "backup.zip",
            ".hidden/notes.js", "css/.env", "css/.hidden.css",
        ]

        for filename in private_files:
            file_path = self.root / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("DUMMY_PRIVATE_CONTENT")

            with self.subTest(filename=filename):
                response = self.client.get("/static/" + filename)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn("DUMMY_PRIVATE_CONTENT", response.text)

    def test_public_styles_and_scripts_can_still_be_downloaded(self):
        for filename in ("style.css", "camera.js", "images/icon.svg"):
            file_path = self.root / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("public asset")

            with self.subTest(filename=filename):
                response = self.client.get("/static/" + filename)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.text, "public asset")

    def test_symlinks_cannot_expose_files_outside_static_directory(self):
        with tempfile.TemporaryDirectory() as outside_directory:
            outside_file = Path(outside_directory) / "private.js"
            outside_file.write_text("OUTSIDE_PRIVATE_CONTENT")
            (self.root / "linked.js").symlink_to(outside_file)

            response = self.client.get("/static/linked.js")
            self.assertEqual(response.status_code, 404)
            self.assertNotIn("OUTSIDE_PRIVATE_CONTENT", response.text)


if __name__ == "__main__":
    unittest.main()
