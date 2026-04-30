import os
import tempfile
from src.obsidian import format_entry, append_to_inbox

CATEGORY_ICONS = {
    "Software": "🖥️",
    "Serie": "🎬",
    "Película": "🎬",
    "Música": "🎵",
}


def test_format_entry_software():
    items = [{"category": "Software", "name": "Cursor", "description": "Editor de código con IA"}]
    url = "https://www.tiktok.com/@user/video/123"
    result = format_entry(items, url, date_str="2026-03-23")
    assert "🖥️" in result
    assert "**Software**" in result
    assert "Cursor" in result
    assert url in result


def test_format_entry_multiple_items():
    items = [
        {"category": "Software", "name": "Cursor", "description": "Editor con IA"},
        {"category": "Serie", "name": "Severance", "description": "Thriller en Apple TV+"},
    ]
    result = format_entry(items, "https://tiktok.com/v/1", date_str="2026-03-23")
    assert "🖥️" in result
    assert "🎬" in result
    assert "Cursor" in result
    assert "Severance" in result


def test_format_entry_no_transcription():
    result = format_entry([], "https://tiktok.com/v/1", date_str="2026-03-23", failed=True)
    assert "no se pudo transcribir" in result.lower()


def test_append_to_inbox_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_path = os.path.join(tmpdir, "VideoInbox.md")
        entry = "- 🖥️ **Software**: Cursor — \"Editor con IA\"\n  [enlace](https://tiktok.com/v/1)\n"
        append_to_inbox(inbox_path, entry, date_str="2026-03-23")

        with open(inbox_path, "r") as f:
            content = f.read()
        assert "## 2026-03-23" in content
        assert "Cursor" in content


def test_append_to_inbox_groups_same_date():
    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_path = os.path.join(tmpdir, "VideoInbox.md")
        entry1 = "- 🖥️ **Software**: Cursor — \"Editor con IA\"\n  [enlace](https://tiktok.com/v/1)\n"
        entry2 = "- 🎬 **Serie**: Severance — \"Thriller\"\n  [enlace](https://tiktok.com/v/2)\n"
        append_to_inbox(inbox_path, entry1, date_str="2026-03-23")
        append_to_inbox(inbox_path, entry2, date_str="2026-03-23")

        with open(inbox_path, "r") as f:
            content = f.read()
        assert content.count("## 2026-03-23") == 1
        assert "Cursor" in content
        assert "Severance" in content
