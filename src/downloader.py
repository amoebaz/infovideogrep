# src/downloader.py
import os
import subprocess
from src.telegram import download_telegram_file


class DurationExceeded(Exception):
    def __init__(self, duration: int, max_duration: int):
        self.duration = duration
        self.max_duration = max_duration
        super().__init__(f"Duration {duration}s exceeds max {max_duration}s")


def _ytdlp_probe_duration(url: str) -> int | None:
    """Return video duration in seconds, or None if it can't be determined."""
    result = subprocess.run(
        ["yt-dlp", "--no-warnings", "--skip-download", "--print", "%(duration)s", url],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        return None
    out = result.stdout.strip().splitlines()
    if not out:
        return None
    try:
        return int(float(out[-1]))
    except ValueError:
        return None


def _download_with_ytdlp(url: str, dest_dir: str) -> str:
    output_template = os.path.join(dest_dir, "%(id)s.%(ext)s")
    result = subprocess.run(
        [
            "yt-dlp",
            "--no-playlist",
            "-o", output_template,
            "--print", "after_move:filepath",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")

    filepath = result.stdout.strip().splitlines()[-1]
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"yt-dlp output not found: {filepath}")
    return filepath


def download_video(
    parsed: dict,
    dest_dir: str,
    bot_token: str,
    max_duration_seconds: int | None = None,
) -> str:
    if parsed["type"] == "url":
        if max_duration_seconds:
            duration = _ytdlp_probe_duration(parsed["url"])
            if duration is not None and duration > max_duration_seconds:
                raise DurationExceeded(duration, max_duration_seconds)
        return _download_with_ytdlp(parsed["url"], dest_dir)
    elif parsed["type"] == "video":
        duration = parsed.get("duration")
        if max_duration_seconds and duration and duration > max_duration_seconds:
            raise DurationExceeded(duration, max_duration_seconds)
        file_id = parsed["file_id"]
        dest_path = os.path.join(dest_dir, f"{file_id}.mp4")
        return download_telegram_file(bot_token, file_id, dest_path)
    else:
        raise ValueError(f"Unknown parsed type: {parsed['type']}")
