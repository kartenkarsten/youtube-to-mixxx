#!/usr/bin/env python3
"""Firefox Native Messaging host for the YouTube-to-Mixxx extension."""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HOST_NAME = "org.mixxx.youtube_downloader"
DEFAULT_DOWNLOAD_PATH = "~/Musik/YouTube"
MAX_MESSAGE_SIZE = 1024 * 1024
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
ACTIVE_PROCESS: subprocess.Popen[str] | None = None


class HostError(Exception):
    """An expected error safe to show to the extension user."""


def config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "youtube-to-mixxx" / "config.json"


def load_settings() -> dict[str, str]:
    path = config_path()
    if not path.exists():
        return {"downloadPath": DEFAULT_DOWNLOAD_PATH}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {"downloadPath": normalize_download_path(data.get("downloadPath", DEFAULT_DOWNLOAD_PATH))}
    except (OSError, ValueError, TypeError) as exc:
        raise HostError("Die gespeicherten Einstellungen sind ungültig. Bitte den Download-Ordner neu speichern.") from exc


def normalize_download_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HostError("Bitte einen Download-Ordner angeben.")
    value = value.strip()
    expanded = Path(os.path.expanduser(value))
    if not expanded.is_absolute():
        raise HostError("Der Download-Ordner muss ein absoluter Pfad sein oder mit ~/ beginnen.")
    if "\x00" in value:
        raise HostError("Der Download-Ordner enthält ein ungültiges Zeichen.")
    return value


def save_settings(value: object) -> dict[str, str]:
    normalized = normalize_download_path(value)
    target = config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="config-", dir=target.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump({"downloadPath": normalized}, output, ensure_ascii=False, indent=2)
            output.write("\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"downloadPath": normalized}


def validate_youtube_url(value: object) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise HostError("Ungültige YouTube-Video-URL.")
    try:
        parsed = urlparse(value)
    except ValueError as exc:
        raise HostError("Ungültige YouTube-Video-URL.") from exc
    if parsed.scheme != "https" or parsed.hostname not in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        raise HostError("Es werden ausschließlich YouTube-Videoseiten unterstützt.")
    if parsed.path != "/watch":
        raise HostError("Unterstützt werden normale Videos, keine Shorts oder Live-Seiten.")
    video_id = parse_qs(parsed.query).get("v", [""])[0]
    if not VIDEO_ID_RE.fullmatch(video_id):
        raise HostError("Die YouTube-URL enthält keine gültige Video-ID.")
    return f"https://www.youtube.com/watch?v={video_id}"


def send_message(message: dict[str, object]) -> None:
    encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > MAX_MESSAGE_SIZE:
        encoded = json.dumps({"event": "error", "error": "Antwort zu groß."}).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("=I", len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


def read_message() -> dict[str, object] | None:
    header = sys.stdin.buffer.read(4)
    if not header:
        return None
    if len(header) != 4:
        raise HostError("Unvollständige Native-Messaging-Nachricht.")
    length = struct.unpack("=I", header)[0]
    if length > MAX_MESSAGE_SIZE:
        raise HostError("Native-Messaging-Nachricht überschreitet die erlaubte Größe.")
    payload = sys.stdin.buffer.read(length)
    if len(payload) != length:
        raise HostError("Unvollständige Native-Messaging-Nachricht.")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HostError("Ungültige Native-Messaging-Nachricht.") from exc
    if not isinstance(data, dict):
        raise HostError("Ungültiges Nachrichtenformat.")
    return data


def emit_progress(line: str) -> None:
    match = re.search(r"\[download\]\s+(\d+(?:\.\d+)?)%", line)
    if match:
        send_message({"event": "progress", "percent": min(100, int(float(match.group(1))))})
    elif "Extracting URL" in line or "Extracting webpage" in line:
        send_message({"event": "progress", "message": "Videoinformationen werden geprüft …"})
    elif "Destination:" in line or "Downloading" in line:
        send_message({"event": "progress", "message": "Audio wird heruntergeladen …"})
    elif "Post-process" in line or "Fixing" in line:
        send_message({"event": "progress", "message": "MP3 und Metadaten werden erstellt …"})


def run_download(raw_url: object) -> dict[str, object]:
    global ACTIVE_PROCESS
    url = validate_youtube_url(raw_url)
    settings = load_settings()
    destination = Path(os.path.expanduser(settings["downloadPath"])).resolve()
    try:
        destination.mkdir(parents=True, exist_ok=True)
        if not destination.is_dir() or not os.access(destination, os.W_OK):
            raise HostError("Der Download-Ordner ist nicht beschreibbar.")
    except OSError as exc:
        raise HostError(f"Download-Ordner kann nicht angelegt werden: {exc.strerror or exc}") from exc

    ytdlp = shutil.which("yt-dlp")
    ffmpeg = shutil.which("ffmpeg")
    if not ytdlp:
        raise HostError("yt-dlp ist nicht installiert oder nicht im PATH.")
    if not ffmpeg:
        raise HostError("ffmpeg ist nicht installiert oder nicht im PATH.")

    archive = config_path().parent / "downloaded-ids.txt"
    output_template = str(destination / "%(title).180B [%(id)s].%(ext)s")
    command = [
        ytdlp,
        "--no-playlist",
        "--no-overwrites",
        "--download-archive", str(archive),
        "--match-filters", "media_type=video & live_status=not_live",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "192K",
        "--embed-metadata",
        "--embed-thumbnail",
        "--parse-metadata", "uploader:%(artist)s",
        "--output", output_template,
        "--print", "after_move:__YTMX_FILE__%(filepath)s",
        "--newline",
        "--no-color",
        url,
    ]
    archive.parent.mkdir(parents=True, exist_ok=True)
    send_message({"event": "progress", "message": "YouTube-Video und Live-Status werden geprüft …"})
    try:
        ACTIVE_PROCESS = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        output_path: str | None = None
        archive_duplicate = False
        rejection = False
        error_lines: list[str] = []
        assert ACTIVE_PROCESS.stdout is not None
        for raw_line in ACTIVE_PROCESS.stdout:
            line = raw_line.strip()
            if line.startswith("__YTMX_FILE__"):
                output_path = line.removeprefix("__YTMX_FILE__")
            if "already been recorded in the archive" in line or "has already been downloaded" in line:
                archive_duplicate = True
            if "does not pass filter" in line:
                rejection = True
            if line.startswith("ERROR:"):
                error_lines.append(line.removeprefix("ERROR:").strip())
                error_lines = error_lines[-3:]
            emit_progress(line)
        return_code = ACTIVE_PROCESS.wait()
    except OSError as exc:
        raise HostError(f"yt-dlp konnte nicht gestartet werden: {exc}") from exc
    finally:
        if ACTIVE_PROCESS is not None and ACTIVE_PROCESS.poll() is None:
            ACTIVE_PROCESS.terminate()
            try:
                ACTIVE_PROCESS.wait(timeout=5)
            except subprocess.TimeoutExpired:
                ACTIVE_PROCESS.kill()
                ACTIVE_PROCESS.wait()
        ACTIVE_PROCESS = None

    if rejection:
        raise HostError("Dieses Video ist ein Live-Stream oder kein unterstütztes normales Video.")
    if return_code != 0:
        detail = " ".join(error_lines)
        raise HostError(f"Download/MP3-Konvertierung fehlgeschlagen{': ' + detail if detail else '.'}")
    if archive_duplicate:
        send_message({"event": "done", "duplicate": True, "path": ""})
        return {"duplicate": True}
    if not output_path or not Path(output_path).is_file():
        raise HostError("yt-dlp meldete keinen Fehler, aber es wurde keine MP3-Datei gefunden.")
    send_message({"event": "done", "duplicate": False, "path": output_path})
    return {"path": output_path}


def handle(message: dict[str, object]) -> None:
    action = message.get("action")
    if action == "get_settings":
        send_message({"ok": True, "settings": load_settings()})
    elif action == "set_settings":
        send_message({"ok": True, "settings": save_settings(message.get("downloadPath"))})
    elif action == "download":
        try:
            run_download(message.get("url"))
        except HostError as exc:
            send_message({"event": "error", "error": str(exc)})
    else:
        raise HostError("Nicht unterstützte Aktion.")


def stop_active_process(_signum: int, _frame: object) -> None:
    if ACTIVE_PROCESS is not None and ACTIVE_PROCESS.poll() is None:
        ACTIVE_PROCESS.terminate()
    raise SystemExit(0)


def main() -> int:
    signal.signal(signal.SIGTERM, stop_active_process)
    signal.signal(signal.SIGINT, stop_active_process)
    try:
        message = read_message()
        if message is None:
            return 0
        handle(message)
        return 0
    except HostError as exc:
        send_message({"event": "error", "error": str(exc)})
        return 1
    except Exception as exc:  # Keep diagnostics off stdout, which is the protocol channel.
        print(f"{HOST_NAME}: {exc}", file=sys.stderr)
        try:
            send_message({"event": "error", "error": "Unerwarteter Fehler im lokalen Begleitprogramm."})
        except (BrokenPipeError, OSError):
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
