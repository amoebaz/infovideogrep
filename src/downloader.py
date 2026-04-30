# src/downloader.py
import os
import subprocess
from src.telegram import download_telegram_file


def _download_with_ytdlp(url: str, dest_dir: str) -> str:
    output_template = os.path.join(dest_dir, "%(id)s.%(ext)s")
    # Use --print after_move:filepath to get the exact output path
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


def download_video(parsed: dict, dest_dir: str, bot_token: str) -> str:
    if parsed["type"] == "url":
        return _download_with_ytdlp(parsed["url"], dest_dir)
    elif parsed["type"] == "video":
        file_id = parsed["file_id"]
        dest_path = os.path.join(dest_dir, f"{file_id}.mp4")
        return download_telegram_file(bot_token, file_id, dest_path)
    else:
        raise ValueError(f"Unknown parsed type: {parsed['type']}")
