import re
import httpx

TIKTOK_URL_PATTERN = re.compile(
    r"https?://(?:www\.|vm\.)?tiktok\.com/[^\s]+"
)


def parse_message(message: dict) -> dict | None:
    # Check for forwarded/attached video
    if "video" in message:
        return {
            "type": "video",
            "file_id": message["video"]["file_id"],
        }

    # Check for TikTok URL in text
    text = message.get("text", "")
    match = TIKTOK_URL_PATTERN.search(text)
    if match:
        return {
            "type": "url",
            "url": match.group(0),
        }

    return None


def get_updates(bot_token: str, offset: int | None = None) -> list[dict]:
    params = {"timeout": 10}
    if offset is not None:
        params["offset"] = offset
    response = httpx.get(
        f"https://api.telegram.org/bot{bot_token}/getUpdates",
        params=params,
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("result", [])


def download_telegram_file(bot_token: str, file_id: str, dest_path: str) -> str:
    # Get file path from Telegram
    response = httpx.get(
        f"https://api.telegram.org/bot{bot_token}/getFile",
        params={"file_id": file_id},
        timeout=30.0,
    )
    response.raise_for_status()
    file_path = response.json()["result"]["file_path"]

    # Download the file
    file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    with httpx.stream("GET", file_url, timeout=120.0) as stream:
        stream.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in stream.iter_bytes():
                f.write(chunk)
    return dest_path


def read_offset(offset_file: str) -> int | None:
    try:
        with open(offset_file, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def write_offset(offset_file: str, offset: int) -> None:
    import os
    dirname = os.path.dirname(offset_file)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(offset_file, "w") as f:
        f.write(str(offset))
