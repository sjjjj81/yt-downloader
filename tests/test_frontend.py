import os
import unittest
from app import create_app


class TestFrontend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def test_homepage_loads(self):
        """Verify the homepage route loads successfully."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"YouTube Downloader", response.data)
        self.assertIn(b"url-input", response.data)
        self.assertIn(b"mode-video", response.data)
        self.assertIn(b"quality-select", response.data)
        self.assertIn(b"metadata-preview", response.data)
        self.assertIn(b"video-thumbnail", response.data)
        self.assertIn(b"video-title", response.data)

    def test_css_asset_resolves(self):
        """Verify the CSS file is accessible and non-empty."""
        response = self.client.get("/static/css/style.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"--accent-color", response.data)
        self.assertIn(b"var(--bg-color)", response.data)

    def test_js_asset_resolves(self):
        """Verify the JavaScript file is accessible and non-empty."""
        response = self.client.get("/static/js/app.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"YouTubeDownloader", response.data)
        self.assertIn(b"isValidUrl", response.data)

    def test_health_endpoint(self):
        """Verify the health endpoint still works."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
