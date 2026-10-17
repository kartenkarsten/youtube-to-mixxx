import importlib.util
import io
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


HOST_PATH = Path(__file__).parents[1] / "native_host" / "youtube_to_mixxx.py"
SPEC = importlib.util.spec_from_file_location("youtube_to_mixxx", HOST_PATH)
host = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(host)


class UrlValidationTests(unittest.TestCase):
    def test_normal_watch_url_is_canonicalized(self):
        self.assertEqual(
            host.validate_youtube_url("https://www.youtube.com/watch?v=abcdefghijk&t=12"),
            "https://www.youtube.com/watch?v=abcdefghijk",
        )

    def test_refuses_non_youtube_hosts(self):
        for url in (
            "https://evil.example/watch?v=abcdefghijk",
            "https://youtube.com.evil.example/watch?v=abcdefghijk",
            "http://www.youtube.com/watch?v=abcdefghijk",
        ):
            with self.subTest(url=url), self.assertRaises(host.HostError):
                host.validate_youtube_url(url)

    def test_refuses_shorts_live_routes_and_malformed_ids(self):
        for url in (
            "https://www.youtube.com/shorts/abcdefghijk",
            "https://www.youtube.com/live/abcdefghijk",
            "https://www.youtube.com/watch?v=short",
        ):
            with self.subTest(url=url), self.assertRaises(host.HostError):
                host.validate_youtube_url(url)


class SettingsTests(unittest.TestCase):
    def test_defaults_to_music_youtube_directory(self):
        with tempfile.TemporaryDirectory() as config_home, patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}):
            self.assertEqual(host.load_settings()["downloadPath"], "~/Musik/YouTube")

    def test_round_trips_settings_and_rejects_relative_paths(self):
        with tempfile.TemporaryDirectory() as config_home, patch.dict(os.environ, {"XDG_CONFIG_HOME": config_home}):
            saved = host.save_settings("~/Musik/YouTube")
            self.assertEqual(saved, {"downloadPath": "~/Musik/YouTube"})
            self.assertEqual(host.load_settings(), saved)
            self.assertEqual(host.config_path().stat().st_mode & 0o777, 0o600)
            with self.assertRaises(host.HostError):
                host.save_settings("relative/music")


class NativeMessagingTests(unittest.TestCase):
    def test_reads_native_message_frame(self):
        payload = json.dumps({"action": "get_settings"}).encode("utf-8")
        stream = io.BytesIO(struct.pack("=I", len(payload)) + payload)
        with patch.object(host.sys, "stdin", type("Input", (), {"buffer": stream})()):
            self.assertEqual(host.read_message(), {"action": "get_settings"})

    def test_writes_native_message_frame(self):
        stream = io.BytesIO()
        with patch.object(host.sys, "stdout", type("Output", (), {"buffer": stream})()):
            host.send_message({"ok": True})
        result = stream.getvalue()
        length = struct.unpack("=I", result[:4])[0]
        self.assertEqual(json.loads(result[4:4 + length]), {"ok": True})


class DownloadFailureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.config = self.root / "config.json"
        self.destination = self.root / "music"
        self.config.write_text(json.dumps({"downloadPath": str(self.destination)}), encoding="utf-8")

    def test_reports_missing_ytdlp(self):
        with patch.object(host, "config_path", return_value=self.config), \
                patch.object(host.shutil, "which", return_value=None), \
                patch.object(host, "send_message"):
            with self.assertRaisesRegex(host.HostError, "yt-dlp"):
                host.run_download("https://www.youtube.com/watch?v=abcdefghijk")

    def test_reports_missing_ffmpeg(self):
        find_tool = lambda name: "/usr/bin/yt-dlp" if name == "yt-dlp" else None
        with patch.object(host, "config_path", return_value=self.config), \
                patch.object(host.shutil, "which", side_effect=find_tool), \
                patch.object(host, "send_message"):
            with self.assertRaisesRegex(host.HostError, "ffmpeg"):
                host.run_download("https://www.youtube.com/watch?v=abcdefghijk")

    def test_reports_unwritable_download_directory(self):
        with patch.object(host, "config_path", return_value=self.config), \
                patch.object(Path, "mkdir", side_effect=PermissionError("read-only filesystem")):
            with self.assertRaisesRegex(host.HostError, "Download-Ordner kann nicht angelegt werden"):
                host.run_download("https://www.youtube.com/watch?v=abcdefghijk")

    def test_terminating_native_host_terminates_active_downloader(self):
        process = Mock()
        process.poll.return_value = None
        with patch.object(host, "ACTIVE_PROCESS", process):
            with self.assertRaises(SystemExit):
                host.stop_active_process(15, None)
        process.terminate.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
