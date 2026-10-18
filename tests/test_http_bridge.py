import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


SERVICE_DIR = Path(__file__).parents[1] / "local_service"
sys.path.insert(0, str(SERVICE_DIR))
import http_bridge


class QuietBridgeHandler(http_bridge.BridgeHandler):
    def log_message(self, format, *args):
        pass


class HttpBridgeTests(unittest.TestCase):
    def setUp(self):
        self.token_patch = patch.object(http_bridge, "BRIDGE_TOKEN", "unit-test-bridge-token-123456789")
        self.token_patch.start()
        self.server = ThreadingHTTPServer((http_bridge.HOST, 0), QuietBridgeHandler)
        self.port = self.server.server_address[1]
        self.port_patch = patch.object(http_bridge, "PORT", self.port)
        self.port_patch.start()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.port_patch.stop)
        self.addCleanup(self.token_patch.stop)

    def post(self, origin, token="unit-test-bridge-token-123456789"):
        request = urllib.request.Request(
            f"http://{http_bridge.HOST}:{self.port}/download",
            data=json.dumps({"url": "https://www.youtube.com/watch?v=abcdefghijk"}).encode(),
            headers={
                "Origin": origin,
                "X-YTMX-Bridge": "tampermonkey",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            response = urllib.request.urlopen(request)
            return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            try:
                return error.code, json.loads(error.read())
            finally:
                error.close()

    def test_token_endpoint_is_not_cors_readable(self):
        request = urllib.request.Request(
            f"http://{http_bridge.HOST}:{self.port}/token",
            headers={"Origin": http_bridge.ALLOWED_ORIGIN},
        )
        response = urllib.request.urlopen(request)
        self.assertEqual(json.loads(response.read()), {"token": "unit-test-bridge-token-123456789"})
        self.assertIsNone(response.headers.get("Access-Control-Allow-Origin"))

    def test_preflight_allows_only_required_download_headers(self):
        request = urllib.request.Request(
            f"http://{http_bridge.HOST}:{self.port}/download",
            headers={
                "Origin": http_bridge.ALLOWED_ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization, content-type, x-ytmx-bridge",
            },
            method="OPTIONS",
        )
        response = urllib.request.urlopen(request)
        self.assertEqual(response.status, 204)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), http_bridge.ALLOWED_ORIGIN)

    def test_creates_persistent_private_token(self):
        with tempfile.TemporaryDirectory() as config_home:
            config = Path(config_home) / "youtube-to-mixxx" / "config.json"
            with patch.object(http_bridge.downloader, "config_path", return_value=config):
                token = http_bridge.load_or_create_bridge_token()
                path = config.parent / "bridge-token"
                self.assertEqual(http_bridge.load_or_create_bridge_token(), token)
            self.assertGreaterEqual(len(token), 40)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_rejects_other_web_origins(self):
        status, response = self.post("https://attacker.example")
        self.assertEqual(status, 403)
        self.assertEqual(response["error"], "Zugriff verweigert.")

    def test_rejects_invalid_bridge_token(self):
        status, response = self.post(http_bridge.ALLOWED_ORIGIN, token="wrong-token")
        self.assertEqual(status, 403)
        self.assertEqual(response["error"], "Zugriff verweigert.")

    def test_accepts_youtube_origin_and_returns_download_result(self):
        with patch.object(http_bridge.downloader, "run_download", return_value={"path": "/music/song.mp3"}) as run:
            status, response = self.post(http_bridge.ALLOWED_ORIGIN)
        self.assertEqual(status, 200)
        self.assertEqual(response, {"ok": True, "duplicate": False, "path": "/music/song.mp3"})
        run.assert_called_once_with("https://www.youtube.com/watch?v=abcdefghijk")


if __name__ == "__main__":
    unittest.main()
