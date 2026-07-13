import os
import tempfile
from datetime import datetime

from src.obsidian import (
    format_entry,
    append_to_markdown,
    route_items,
    save_transcription,
    update_estado,
    mark_processed,
    PENDING_DIR,
    PROCESSED_DIR,
)


CATEGORY_ICONS = {
    "Software": "🖥️",
    "Serie": "📺",
    "Película": "🎬",
    "Música": "🎵",
}


def test_format_entry_software():
    items = [{"category": "Software", "name": "Cursor", "description": "Editor de código con IA"}]
    url = "https://www.tiktok.com/@user/video/123"
    result = format_entry(items, url, date_str="2026-03-23", category_icons=CATEGORY_ICONS)
    assert "🖥️" in result
    assert "**Software**" in result
    assert "Cursor" in result
    assert url in result


def test_format_entry_multiple_items():
    items = [
        {"category": "Software", "name": "Cursor", "description": "Editor con IA"},
        {"category": "Serie", "name": "Severance", "description": "Thriller en Apple TV+"},
    ]
    result = format_entry(items, "https://tiktok.com/v/1", date_str="2026-03-23", category_icons=CATEGORY_ICONS)
    assert "🖥️" in result
    assert "📺" in result
    assert "Cursor" in result
    assert "Severance" in result


def test_format_entry_unknown_category_uses_default_icon():
    items = [{"category": "Receta", "name": "Tortilla", "description": "Patata"}]
    result = format_entry(items, "https://tiktok.com/v/1", date_str="2026-03-23", category_icons=CATEGORY_ICONS)
    assert "📌" in result
    assert "**Receta**" in result


def test_format_entry_no_transcription():
    result = format_entry([], "https://tiktok.com/v/1", date_str="2026-03-23", category_icons=CATEGORY_ICONS, failed=True)
    assert "no se pudo transcribir" in result.lower()


def test_append_to_markdown_creates_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "VideoInbox.md")
        entry = "- 🖥️ **Software**: Cursor — \"Editor con IA\"\n  [enlace](https://tiktok.com/v/1)\n"
        append_to_markdown(path, entry, date_str="2026-03-23")

        with open(path, "r") as f:
            content = f.read()
        assert "## 2026-03-23" in content
        assert "Cursor" in content


def test_append_to_markdown_groups_same_date():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "VideoInbox.md")
        entry1 = "- 🖥️ **Software**: Cursor — \"Editor con IA\"\n  [enlace](https://tiktok.com/v/1)\n"
        entry2 = "- 📺 **Serie**: Severance — \"Thriller\"\n  [enlace](https://tiktok.com/v/2)\n"
        append_to_markdown(path, entry1, date_str="2026-03-23")
        append_to_markdown(path, entry2, date_str="2026-03-23")

        with open(path, "r") as f:
            content = f.read()
        assert content.count("## 2026-03-23") == 1
        assert "Cursor" in content
        assert "Severance" in content


SUMMARY_FILES = [
    {"file": "Series y Películas.md", "categories": ["Serie", "Película"]},
    {"file": "Software.md", "categories": ["Software"]},
    {"file": "IA.md", "categories": ["IA"]},
]


def test_route_items_maps_categories_to_files():
    items = [
        {"category": "Serie", "name": "Severance", "description": "d"},
        {"category": "Película", "name": "Dune", "description": "d"},
        {"category": "Software", "name": "Cursor", "description": "d"},
    ]
    routed = route_items(items, SUMMARY_FILES, default_file="Otros.md")
    assert [i["name"] for i in routed["Series y Películas.md"]] == ["Severance", "Dune"]
    assert [i["name"] for i in routed["Software.md"]] == ["Cursor"]
    assert "Otros.md" not in routed


def test_route_items_unmapped_category_goes_to_default():
    items = [{"category": "Receta", "name": "Tortilla", "description": "d"}]
    routed = route_items(items, SUMMARY_FILES, default_file="Otros.md")
    assert [i["name"] for i in routed["Otros.md"]] == ["Tortilla"]


def test_route_items_empty():
    assert route_items([], SUMMARY_FILES, default_file="Otros.md") == {}


DT = datetime(2026, 7, 13, 18, 42)


def test_save_transcription_creates_pending_file():
    with tempfile.TemporaryDirectory() as vault:
        path = save_transcription(
            vault, url="https://youtu.be/abc", text="Texto completo del vídeo",
            dt=DT, slug="youtube",
        )
        assert os.path.dirname(path) == os.path.join(vault, PENDING_DIR)
        assert os.path.basename(path) == "2026-07-13 18-42 - youtube.md"
        with open(path) as f:
            content = f.read()
        assert "estado: pendiente" in content
        assert "intentos: 0" in content
        assert "url: https://youtu.be/abc" in content
        assert "fecha: 2026-07-13T18:42:00" in content
        assert "Texto completo del vídeo" in content


def test_save_transcription_terminal_state_goes_to_processed():
    with tempfile.TemporaryDirectory() as vault:
        path = save_transcription(
            vault, url="https://youtu.be/abc", text="Duración excedida.",
            dt=DT, slug="youtube", estado="duracion_excedida",
        )
        assert os.path.dirname(path) == os.path.join(vault, PROCESSED_DIR)
        with open(path) as f:
            assert "estado: duracion_excedida" in f.read()


def test_save_transcription_collision_adds_suffix():
    with tempfile.TemporaryDirectory() as vault:
        first = save_transcription(vault, url="u1", text="a", dt=DT, slug="tiktok")
        second = save_transcription(vault, url="u2", text="b", dt=DT, slug="tiktok")
        assert first != second
        assert os.path.basename(second) == "2026-07-13 18-42 - tiktok (2).md"


def test_save_transcription_sanitizes_slug_for_windows():
    with tempfile.TemporaryDirectory() as vault:
        path = save_transcription(vault, url="u", text="a", dt=DT, slug='vi:de*o?"raro"')
        for char in ':*?"':
            assert char not in os.path.basename(path)


def test_update_estado_rewrites_frontmatter_only():
    with tempfile.TemporaryDirectory() as vault:
        path = save_transcription(vault, url="u", text="estado: falso en el cuerpo no se toca", dt=DT, slug="x")
        update_estado(path, "error_llm", intentos=1)
        with open(path) as f:
            content = f.read()
        assert "estado: error_llm" in content
        assert "intentos: 1" in content
        assert "estado: falso en el cuerpo no se toca" in content


def test_update_estado_url_with_triple_dash_does_not_corrupt():
    with tempfile.TemporaryDirectory() as vault:
        path = save_transcription(
            vault, url="https://example.com/v?id=a---b", text="cuerpo", dt=DT, slug="x"
        )
        update_estado(path, "error_llm", intentos=1)
        with open(path) as f:
            content = f.read()
        assert "estado: error_llm" in content
        assert "intentos: 1" in content
        assert "url: https://example.com/v?id=a---b" in content
        assert "cuerpo" in content


def test_mark_processed_moves_to_processed_dir():
    with tempfile.TemporaryDirectory() as vault:
        path = save_transcription(vault, url="u", text="hola", dt=DT, slug="youtube")
        new_path = mark_processed(path, vault)
        assert not os.path.exists(path)
        assert os.path.dirname(new_path) == os.path.join(vault, PROCESSED_DIR)
        with open(new_path) as f:
            content = f.read()
        assert "estado: procesada" in content
        assert "hola" in content
