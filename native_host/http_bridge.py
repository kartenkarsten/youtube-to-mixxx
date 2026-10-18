#!/usr/bin/env python3
"""Local HTTP bridge for the Tampermonkey userscript."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any

import youtube_to_mixxx as downloader

HOST = "127.0.0.1"
PORT = 8765
ALLOWED_ORIGIN = "https://www.youtube.com"
MAX_BODY_SIZE = 16 * 1024
DOWNLOAD_LOCK = Lock()


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "YouTubeToMixxxBridge/1.0"

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if self.headers.get("Origin") == ALLOWED_ORIGIN:
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
        if (
            not self._request_is_local_youtube(require_bridge_header=False)
            or "x-ytmx-bridge" not in requested_headers
        ):
            self._send_json(403, {"error": "Zugriff verweigert."})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-YTMX-Bridge")
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Vary", "Origin")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path != "/download" or not self._request_is_local_youtube():
            self._send_json(403, {"error": "Zugriff verweigert."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY_SIZE:
                raise downloader.HostError("Ungültige Anfragegröße.")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise downloader.HostError("Ungültiges Nachrichtenformat.")
            with DOWNLOAD_LOCK:
                result = downloader.run_download(payload.get("url"), notify=lambda _event: None)
            self._send_json(200, {"ok": True, "duplicate": bool(result.get("duplicate")), "path": result.get("path", "")})
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "Ungültiges JSON."})
        except downloader.HostError as exc:
            self._send_json(400, {"error": str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            print(f"Tampermonkey bridge: {exc}", flush=True)
            self._send_json(500, {"error": "Unerwarteter Fehler im lokalen Begleitprogramm."})

    def log_message(self, format: str, *args: object) -> None:
        print(f"Tampermonkey bridge: {format % args}", flush=True)


def main() -> None:
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
