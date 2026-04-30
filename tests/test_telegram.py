from src.telegram import parse_message


def test_parse_message_with_tiktok_url():
    message = {
        "message_id": 1,
        "text": "Mira esto https://www.tiktok.com/@user/video/1234567890",
    }
    result = parse_message(message)
    assert result["type"] == "url"
    assert result["url"] == "https://www.tiktok.com/@user/video/1234567890"


def test_parse_message_with_vm_tiktok_url():
    message = {
        "message_id": 2,
        "text": "https://vm.tiktok.com/ZMhABC123/",
    }
    result = parse_message(message)
    assert result["type"] == "url"
    assert result["url"] == "https://vm.tiktok.com/ZMhABC123/"


def test_parse_message_with_youtube_watch_url():
    message = {
        "message_id": 10,
        "text": "Mira https://www.youtube.com/watch?v=dQw4w9WgXcQ y comenta",
    }
    result = parse_message(message)
    assert result["type"] == "url"
    assert result["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_parse_message_with_youtube_shorts_url():
    message = {
        "message_id": 11,
        "text": "https://www.youtube.com/shorts/abcDEF12345",
    }
    result = parse_message(message)
    assert result["type"] == "url"
    assert result["url"] == "https://www.youtube.com/shorts/abcDEF12345"


def test_parse_message_with_youtu_be_url():
    message = {
        "message_id": 12,
        "text": "https://youtu.be/dQw4w9WgXcQ",
    }
    result = parse_message(message)
    assert result["type"] == "url"
    assert result["url"] == "https://youtu.be/dQw4w9WgXcQ"


def test_parse_message_with_instagram_reel_url():
    message = {
        "message_id": 20,
        "text": "https://www.instagram.com/reel/CxYz123abc/",
    }
    result = parse_message(message)
    assert result["type"] == "url"
    assert result["url"] == "https://www.instagram.com/reel/CxYz123abc/"


def test_parse_message_with_instagram_reels_url():
    message = {
        "message_id": 21,
        "text": "https://instagram.com/reels/CxYz123abc/",
    }
    result = parse_message(message)
    assert result["type"] == "url"
    assert result["url"] == "https://instagram.com/reels/CxYz123abc/"


def test_parse_message_with_forwarded_video():
    message = {
        "message_id": 3,
        "video": {"file_id": "ABCDEF123", "file_size": 5000000, "duration": 42},
    }
    result = parse_message(message)
    assert result["type"] == "video"
    assert result["file_id"] == "ABCDEF123"
    assert result["duration"] == 42


def test_parse_message_irrelevant_text():
    message = {
        "message_id": 4,
        "text": "Hola, qué tal?",
    }
    result = parse_message(message)
    assert result is None


def test_parse_message_empty():
    message = {"message_id": 5}
    result = parse_message(message)
    assert result is None
