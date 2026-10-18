#!/usr/bin/env python3
"""Local HTTP bridge for the Tampermonkey userscript."""

from __future__ import annotations

import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any

import downloader

HOST = "127.0.0.1"
PORT = 8765
ALLOWED_ORIGIN = "https://www.youtube.com"
MAX_BODY_SIZE = 16 * 1024
DOWNLOAD_LOCK = Lock()
BRIDGE_TOKEN = ""


def load_or_create_bridge_token() -> str:
    token_path = downloader.config_path().parent / "bridge-token"
    token_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        token = token_path.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        token = secrets.token_urlsafe(32)
        try:
            fd = os.open(token_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            token = token_path.read_text(encoding="ascii").strip()
        else:
            with os.fdopen(fd, "w", encoding="ascii") as output:
                output.write(token + "\n")
    if len(token) < 40:
        raise RuntimeError("Lokales Bridge-Token fehlt oder ist ungültig.")
    os.chmod(token_path, 0o600)
    return token


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "YouTubeToMixxxBridge/1.0"

    def _send_json(self, status: int, payload: dict[str, Any], *, allow_cors: bool = True) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if allow_cors and self.headers.get("Origin") == ALLOWED_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
            self.send_header("Vary", "Origin")
        self.end_headers()
        self.wfile.write(body)

    def _request_is_local_youtube(self, *, require_bridge_header: bool = True) -> bool:
        # Binding to loopback and checking both headers prevents other sites from
        # using this local downloader through ordinary browser requests. Firefox
        # may identify a privileged Tampermonkey request with its extension origin
        # (or omit Origin), so those forms are accepted alongside YouTube itself.
        origin = self.headers.get("Origin", "")
        allowed_origin = (
            origin in {"", ALLOWED_ORIGIN}
            or origin.startswith("moz-extension://")
        )
        return (
            self.headers.get("Host") == f"{HOST}:{PORT}"
            and allowed_origin
            and (
                not require_bridge_header
                or self.headers.get("X-YTMX-Bridge") == "tampermonkey"
            )
        )

    def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib handler API
        requested_headers = {
            header.strip().lower()
            for header in self.headers.get("Access-Control-Request-Headers", "").split(",")
        }
        if self.path != "/download" or self.headers.get("Access-Control-Request-Method") != "POST" or (
            not self._request_is_local_youtube(require_bridge_header=False)
            or not {"x-ytmx-bridge", "authorization", "content-type"}.issubset(requested_headers)
        ):
            self._send_json(403, {"error": "Zugriff verweigert."})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-YTMX-Bridge")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path != "/token" or not self._request_is_local_youtube(require_bridge_header=False):
            self._send_json(403, {"error": "Zugriff verweigert."}, allow_cors=False)
            return
        # Tampermonkey's privileged request can read this response; normal page
        # scripts cannot because this endpoint deliberately omits CORS headers.
        self._send_json(200, {"token": BRIDGE_TOKEN}, allow_cors=False)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        supplied_token = self.headers.get("Authorization", "")
        expected_token = f"Bearer {BRIDGE_TOKEN}"
        if (
            self.path != "/download"
            or not self._request_is_local_youtube()
            or not secrets.compare_digest(supplied_token, expected_token)
        ):
            self._send_json(403, {"error": "Zugriff verweigert."})
            return
        try:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._send_json(400, {"error": "Ungültige Anfragegröße."})
                return
            if length <= 0 or length > MAX_BODY_SIZE:
                raise downloader.DownloadError("Ungültige Anfragegröße.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise downloader.DownloadError("Ungültiges Nachrichtenformat.")
            with DOWNLOAD_LOCK:
                result = downloader.run_download(payload.get("url"))
            self._send_json(200, {"ok": True, "duplicate": bool(result.get("duplicate")), "path": result.get("path", "")})
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "Ungültiges JSON."})
        except downloader.DownloadError as exc:
            self._send_json(400, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            print(f"Tampermonkey bridge: {exc}", flush=True)
            self._send_json(500, {"error": "Unerwarteter Fehler im lokalen Begleitprogramm."})

    def log_message(self, format: str, *args: object) -> None:
        print(f"Tampermonkey bridge: {format % args}", flush=True)


def main() -> None:
    global BRIDGE_TOKEN
    BRIDGE_TOKEN = load_or_create_bridge_token()
    server = ThreadingHTTPServer((HOST, PORT), BridgeHandler)
    print(f"Tampermonkey bridge listening on http://{HOST}:{PORT}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
