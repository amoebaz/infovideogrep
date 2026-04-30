# tests/test_downloader.py
import os
import tempfile
from unittest.mock import patch, MagicMock
from src.downloader import download_video


def test_download_url_calls_ytdlp():
    with tempfile.TemporaryDirectory() as tmpdir:
        parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/123"}
        with patch("src.downloader._download_with_ytdlp") as mock_yt:
            mock_yt.return_value = os.path.join(tmpdir, "video.mp4")
            result = download_video(parsed, tmpdir, bot_token="")
            mock_yt.assert_called_once_with(
                "https://www.tiktok.com/@user/video/123", tmpdir
            )
            assert result == os.path.join(tmpdir, "video.mp4")


def test_download_forwarded_video_calls_telegram():
    with tempfile.TemporaryDirectory() as tmpdir:
        parsed = {"type": "video", "file_id": "ABC123"}
        with patch("src.downloader.download_telegram_file") as mock_tg:
            expected_path = os.path.join(tmpdir, "ABC123.mp4")
            mock_tg.return_value = expected_path
            result = download_video(parsed, tmpdir, bot_token="TOKEN")
            mock_tg.assert_called_once_with("TOKEN", "ABC123", expected_path)
            assert result == expected_path
