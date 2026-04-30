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


def test_parse_message_with_forwarded_video():
    message = {
        "message_id": 3,
        "video": {"file_id": "ABCDEF123", "file_size": 5000000},
    }
    result = parse_message(message)
    assert result["type"] == "video"
    assert result["file_id"] == "ABCDEF123"


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
