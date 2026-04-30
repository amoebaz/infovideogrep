import re
import httpx

VIDEO_URL_PATTERN = re.compile(
    r"https?://"
    r"(?:"
        r"(?:www\.|vm\.)?tiktok\.com/[^\s]+"
        r"|(?:www\.|m\.)?youtube\.com/(?:watch\?[^\s]+|shorts/[^\s]+)"
        r"|youtu\.be/[^\s]+"
        r"|(?:www\.)?instagram\.com/reels?/[^\s]+"
    r")"
)


def parse_message(message: dict) -> dict | None:
    if "video" in message:
        return {
            "type": "video",
            "file_id": message["video"]["file_id"],
            "duration": message["video"].get("duration"),
        }

    text = message.get("text", "")
    match = VIDEO_URL_PATTERN.search(text)
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
    response = httpx.get(
        f"https://api.telegram.org/bot{bot_token}/getFile",
        params={"file_id": file_id},
        timeout=30.0,
    )
    response.raise_for_status()
    file_path = response.json()["result"]["file_path"]

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
