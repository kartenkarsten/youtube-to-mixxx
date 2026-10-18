#!/usr/bin/env python3
"""Shared YouTube-to-Mixxx downloader used by the local HTTP bridge."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DEFAULT_DOWNLOAD_PATH = "~/Musik/YouTube"
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
ACTIVE_PROCESS: subprocess.Popen[str] | None = None


class DownloadError(Exception):
    """An expected download/configuration error safe to show to the user."""


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
        raise DownloadError("Die gespeicherten Einstellungen sind ungültig. Bitte den Download-Ordner prüfen.") from exc


def normalize_download_path(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DownloadError("Bitte einen Download-Ordner angeben.")
    value = value.strip()
    expanded = Path(os.path.expanduser(value))
    if not expanded.is_absolute():
        raise DownloadError("Der Download-Ordner muss ein absoluter Pfad sein oder mit ~/ beginnen.")
    if "\x00" in value:
        raise DownloadError("Der Download-Ordner enthält ein ungültiges Zeichen.")
    return value


def validate_youtube_url(value: object) -> str:
    if not isinstance(value, str) or len(value) > 2048:
        raise DownloadError("Ungültige YouTube-Video-URL.")
    try:
        parsed = urlparse(value)
    except ValueError as exc:
        raise DownloadError("Ungültige YouTube-Video-URL.") from exc
    if parsed.scheme != "https" or parsed.hostname not in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        raise DownloadError("Es werden ausschließlich YouTube-Videoseiten unterstützt.")
    if parsed.path != "/watch":
        raise DownloadError("Unterstützt werden normale Videos, keine Shorts oder Live-Seiten.")
    video_id = parse_qs(parsed.query).get("v", [""])[0]
    if not VIDEO_ID_RE.fullmatch(video_id):
        raise DownloadError("Die YouTube-URL enthält keine gültige Video-ID.")
    return f"https://www.youtube.com/watch?v={video_id}"


def run_download(raw_url: object) -> dict[str, object]:
    global ACTIVE_PROCESS
    url = validate_youtube_url(raw_url)
    settings = load_settings()
    destination = Path(os.path.expanduser(settings["downloadPath"])).resolve()
    try:
        destination.mkdir(parents=True, exist_ok=True)
        if not destination.is_dir() or not os.access(destination, os.W_OK):
            raise DownloadError("Der Download-Ordner ist nicht beschreibbar.")
    except OSError as exc:
        raise DownloadError(f"Download-Ordner kann nicht angelegt werden: {exc.strerror or exc}") from exc

    ytdlp = shutil.which("yt-dlp")
    ffmpeg = shutil.which("ffmpeg")
    if not ytdlp:
        raise DownloadError("yt-dlp ist nicht installiert oder nicht im PATH.")
    if not ffmpeg:
        raise DownloadError("ffmpeg ist nicht installiert oder nicht im PATH.")

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
        return_code = ACTIVE_PROCESS.wait()
    except OSError as exc:
        raise DownloadError(f"yt-dlp konnte nicht gestartet werden: {exc}") from exc
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
        raise DownloadError("Dieses Video ist ein Live-Stream oder kein unterstütztes normales Video.")
    if return_code != 0:
        detail = " ".join(error_lines)
        raise DownloadError(f"Download/MP3-Konvertierung fehlgeschlagen{': ' + detail if detail else '.'}")
    if archive_duplicate:
        return {"duplicate": True}
    if not output_path or not Path(output_path).is_file():
        raise DownloadError("yt-dlp meldete keinen Fehler, aber es wurde keine MP3-Datei gefunden.")
    return {"path": output_path}
