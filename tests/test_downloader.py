import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


DOWNLOADER_PATH = Path(__file__).parents[1] / "local_service" / "downloader.py"
SPEC = importlib.util.spec_from_file_location("downloader", DOWNLOADER_PATH)
downloader = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(downloader)


class UrlValidationTests(unittest.TestCase):
    def test_normal_watch_url_is_canonicalized(self):
        self.assertEqual(
            downloader.validate_youtube_url("https://www.youtube.com/watch?v=abcdefghijk&t=12"),
            "https://www.youtube.com/watch?v=abcdefghijk",
        )

    def test_refuses_non_youtube_hosts(self):
        for url in (
            "https://evil.example/watch?v=abcdefghijk",
            "https://youtube.com.evil.example/watch?v=abcdefghijk",
            "http://www.youtube.com/watch?v=abcdefghijk",
        ):
            with self.subTest(url=url), self.assertRaises(downloader.DownloadError):
                downloader.validate_youtube_url(url)

    def test_refuses_shorts_live_routes_and_malformed_ids(self):
        for url in (
            "https://www.youtube.com/shorts/abcdefghijk",
            "https://www.youtube.com/live/abcdefghijk",
            "https://www.youtube.com/watch?v=short",
        ):
            with self.subTest(url=url), self.assertRaises(downloader.DownloadError):
                downloader.validate_youtube_url(url)


class SettingsTests(unittest.TestCase):
    def test_defaults_to_music_youtube_directory(self):
        with tempfile.TemporaryDirectory() as config_home, patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}):
            self.assertEqual(downloader.load_settings()["downloadPath"], "~/Musik/YouTube")

    def test_reads_configured_download_path(self):
        with tempfile.TemporaryDirectory() as config_home, patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}):
            settings_path = Path(config_home) / "youtube-to-mixxx" / "config.json"
            settings_path.parent.mkdir()
            settings_path.write_text(json.dumps({"downloadPath": "~/Downloads/Mixxx"}), encoding="utf-8")
            self.assertEqual(downloader.load_settings(), {"downloadPath": "~/Downloads/Mixxx"})

    def test_rejects_relative_download_paths(self):
        with self.assertRaises(downloader.DownloadError):
            downloader.normalize_download_path("relative/music")


class DownloadFailureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = self.root / "config.json"
        self.destination = self.root / "music"
        self.config.write_text(json.dumps({"downloadPath": str(self.destination)}), encoding="utf-8")

    def test_reports_missing_ytdlp(self):
        with patch.object(downloader, "config_path", return_value=self.config), \
                patch.object(downloader.shutil, "which", return_value=None):
            with self.assertRaisesRegex(downloader.DownloadError, "yt-dlp"):
                downloader.run_download("https://www.youtube.com/watch?v=abcdefghijk")

    def test_reports_missing_ffmpeg(self):
        find_tool = lambda name: "/usr/bin/yt-dlp" if name == "yt-dlp" else None
        with patch.object(downloader, "config_path", return_value=self.config), \
                patch.object(downloader.shutil, "which", side_effect=find_tool):
            with self.assertRaisesRegex(downloader.DownloadError, "ffmpeg"):
                downloader.run_download("https://www.youtube.com/watch?v=abcdefghijk")

    def test_reports_unwritable_download_directory(self):
        with patch.object(downloader, "config_path", return_value=self.config), \
                patch.object(Path, "mkdir", side_effect=PermissionError("read-only filesystem")):
            with self.assertRaisesRegex(downloader.DownloadError, "Download-Ordner kann nicht angelegt werden"):
                downloader.run_download("https://www.youtube.com/watch?v=abcdefghijk")


if __name__ == "__main__":
    unittest.main()
