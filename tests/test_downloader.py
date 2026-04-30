# tests/test_downloader.py
import os
import tempfile
import pytest
from unittest.mock import patch
from src.downloader import download_video, DurationExceeded


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


def test_download_url_skips_when_duration_exceeds_max():
    with tempfile.TemporaryDirectory() as tmpdir:
        parsed = {"type": "url", "url": "https://www.youtube.com/watch?v=abc"}
        with (
            patch("src.downloader._ytdlp_probe_duration", return_value=7200),
            patch("src.downloader._download_with_ytdlp") as mock_yt,
        ):
            with pytest.raises(DurationExceeded) as excinfo:
                download_video(parsed, tmpdir, bot_token="", max_duration_seconds=3600)
            assert excinfo.value.duration == 7200
            assert excinfo.value.max_duration == 3600
            mock_yt.assert_not_called()


def test_download_url_proceeds_when_within_max_duration():
    with tempfile.TemporaryDirectory() as tmpdir:
        parsed = {"type": "url", "url": "https://www.youtube.com/shorts/abc"}
        with (
            patch("src.downloader._ytdlp_probe_duration", return_value=45),
            patch("src.downloader._download_with_ytdlp", return_value=os.path.join(tmpdir, "v.mp4")) as mock_yt,
        ):
            result = download_video(parsed, tmpdir, bot_token="", max_duration_seconds=3600)
            mock_yt.assert_called_once()
            assert result.endswith("v.mp4")


def test_download_telegram_video_skips_when_duration_exceeds_max():
    with tempfile.TemporaryDirectory() as tmpdir:
        parsed = {"type": "video", "file_id": "ABC", "duration": 5000}
        with patch("src.downloader.download_telegram_file") as mock_tg:
            with pytest.raises(DurationExceeded):
                download_video(parsed, tmpdir, bot_token="TOKEN", max_duration_seconds=3600)
            mock_tg.assert_not_called()


def test_download_telegram_video_no_duration_metadata_proceeds():
    """If Telegram message lacks duration, we trust and download anyway."""
    with tempfile.TemporaryDirectory() as tmpdir:
        parsed = {"type": "video", "file_id": "ABC"}
        expected = os.path.join(tmpdir, "ABC.mp4")
        with patch("src.downloader.download_telegram_file", return_value=expected) as mock_tg:
            result = download_video(parsed, tmpdir, bot_token="TOKEN", max_duration_seconds=3600)
            mock_tg.assert_called_once()
            assert result == expected


def test_download_url_no_max_duration_skips_probe():
    with tempfile.TemporaryDirectory() as tmpdir:
        parsed = {"type": "url", "url": "https://www.tiktok.com/v/1"}
        with (
            patch("src.downloader._ytdlp_probe_duration") as mock_probe,
            patch("src.downloader._download_with_ytdlp", return_value=os.path.join(tmpdir, "v.mp4")),
        ):
            download_video(parsed, tmpdir, bot_token="")
            mock_probe.assert_not_called()
