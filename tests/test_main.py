import os
import tempfile
from unittest.mock import patch
from src.main import process_message
from src.downloader import DurationExceeded
from src.obsidian import PENDING_DIR, PROCESSED_DIR


CATEGORIES = [
    {"name": "Software", "icon": "🖥️"},
    {"name": "Serie", "icon": "📺"},
    {"name": "Película", "icon": "🎬"},
    {"name": "IA", "icon": "🤖"},
]

LLM_CONFIG = {"base_url": "http://localhost:11434/v1", "api_key": "", "model": "test"}


def _markdown_config(tmpdir):
    return {
        "vault_inbox_dir": os.path.join(tmpdir, "VideoInbox"),
        "summary_files": [
            {"file": "Series y Películas.md", "categories": ["Serie", "Película"]},
            {"file": "Software.md", "categories": ["Software"]},
            {"file": "IA.md", "categories": ["IA"]},
        ],
        "default_summary_file": "Otros.md",
    }


def _only_file(directory):
    files = os.listdir(directory)
    assert len(files) == 1, f"expected 1 file in {directory}, got {files}"
    with open(os.path.join(directory, files[0])) as f:
        return files[0], f.read()


def _run(parsed, markdown_config, tmpdir, **kwargs):
    process_message(
        parsed=parsed,
        bot_token="TOKEN",
        whisper_model="medium",
        llm_config=kwargs.pop("llm_config", LLM_CONFIG),
        markdown_config=markdown_config,
        tmp_dir=tmpdir,
        categories=CATEGORIES,
        **kwargs,
    )


def test_success_writes_summary_and_archives_transcription():
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/123"}
    items = [{"category": "Software", "name": "Cursor", "description": "Editor con IA"}]

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="Hablamos de Cursor"),
            patch("src.main.extract_data", return_value=items),
        ):
            _run(parsed, md, tmpdir)

        with open(os.path.join(md["vault_inbox_dir"], "Software.md")) as f:
            summary = f.read()
        assert "Cursor" in summary
        assert "🖥️" in summary
        assert parsed["url"] in summary

        pending = os.path.join(md["vault_inbox_dir"], PENDING_DIR)
        assert os.listdir(pending) == []
        name, content = _only_file(os.path.join(md["vault_inbox_dir"], PROCESSED_DIR))
        assert "tiktok" in name
        assert "estado: procesada" in content
        assert "Hablamos de Cursor" in content


def test_items_split_across_summary_files():
    parsed = {"type": "url", "url": "https://youtu.be/abc"}
    items = [
        {"category": "Serie", "name": "Severance", "description": "Thriller"},
        {"category": "Software", "name": "Zed", "description": "Editor"},
        {"category": "Receta", "name": "Tortilla", "description": "Patata"},
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="texto"),
            patch("src.main.extract_data", return_value=items),
        ):
            _run(parsed, md, tmpdir)

        vault = md["vault_inbox_dir"]
        with open(os.path.join(vault, "Series y Películas.md")) as f:
            assert "Severance" in f.read()
        with open(os.path.join(vault, "Software.md")) as f:
            assert "Zed" in f.read()
        with open(os.path.join(vault, "Otros.md")) as f:
            assert "Tortilla" in f.read()


def test_llm_failure_leaves_pending_with_error_state():
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/789"}

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="Hablamos de algo interesante"),
            patch("src.main.extract_data", side_effect=Exception("LLM down")),
        ):
            _run(parsed, md, tmpdir)

        _, content = _only_file(os.path.join(md["vault_inbox_dir"], PENDING_DIR))
        assert "estado: error_llm" in content
        assert "intentos: 1" in content
        assert "Hablamos de algo interesante" in content
        assert not os.path.exists(os.path.join(md["vault_inbox_dir"], "Software.md"))


def test_empty_transcription_archived_with_state():
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/456"}

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value=""),
        ):
            _run(parsed, md, tmpdir)

        _, content = _only_file(os.path.join(md["vault_inbox_dir"], PROCESSED_DIR))
        assert "estado: transcripcion_vacia" in content
        assert parsed["url"] in content


def test_duration_exceeded_archived_with_state():
    parsed = {"type": "url", "url": "https://www.youtube.com/watch?v=longone"}

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        with (
            patch("src.main.download_video", side_effect=DurationExceeded(7200, 3600)),
            patch("src.main.transcribe") as mock_tr,
        ):
            _run(parsed, md, tmpdir, max_duration_seconds=3600)
            mock_tr.assert_not_called()

        _, content = _only_file(os.path.join(md["vault_inbox_dir"], PROCESSED_DIR))
        assert "estado: duracion_excedida" in content
        assert "120 min" in content
        assert "60 min" in content


def test_llm_chain_second_model_succeeds():
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/555"}
    llm_config = {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "key",
        "models": ["broken/model:free", "working/model:free"],
    }
    items = [{"category": "Software", "name": "Zed", "description": "Editor rápido"}]

    def mock_extract(text, config, category_names):
        if config["model"] == "working/model:free":
            return items
        raise Exception("404 No endpoints found")

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="Hablamos de Zed"),
            patch("src.main.extract_data", side_effect=mock_extract),
        ):
            _run(parsed, md, tmpdir, llm_config=llm_config)

        with open(os.path.join(md["vault_inbox_dir"], "Software.md")) as f:
            assert "Zed" in f.read()
        assert os.listdir(os.path.join(md["vault_inbox_dir"], PENDING_DIR)) == []


def test_fallback_llm_succeeds():
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/999"}
    llm_config = {"base_url": "https://openrouter.ai/api/v1", "api_key": "key", "model": "remote"}
    fallback_config = {"base_url": "http://localhost:11434/v1", "api_key": "", "model": "qwen2.5:3b"}
    items = [{"category": "Software", "name": "Neovim", "description": "Editor de terminal"}]

    call_count = 0
    def mock_extract(text, config, category_names):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise Exception("OpenRouter overloaded")
        return items

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="Hablamos de Neovim"),
            patch("src.main.extract_data", side_effect=mock_extract),
            patch("src.main._ensure_ollama_running"),
        ):
            _run(parsed, md, tmpdir, llm_config=llm_config, llm_fallback_config=fallback_config)

        with open(os.path.join(md["vault_inbox_dir"], "Software.md")) as f:
            assert "Neovim" in f.read()


def test_llm_succeeds_on_retry():
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/101"}
    items = [{"category": "Software", "name": "Docker", "description": "Contenedores"}]

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="Hablamos de Docker"),
            patch("src.main.extract_data", side_effect=[Exception("timeout"), items]),
        ):
            _run(parsed, md, tmpdir)

        with open(os.path.join(md["vault_inbox_dir"], "Software.md")) as f:
            assert "Docker" in f.read()


def test_no_items_archives_without_summary():
    """LLM responde pero sin items relevantes — se archiva sin escribir resúmenes."""
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/222"}

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="bla bla sin contenido"),
            patch("src.main.extract_data", return_value=[]),
        ):
            _run(parsed, md, tmpdir)

        _, content = _only_file(os.path.join(md["vault_inbox_dir"], PROCESSED_DIR))
        assert "estado: procesada" in content
        assert not os.path.exists(os.path.join(md["vault_inbox_dir"], "Software.md"))


def test_forwarded_video_no_url():
    parsed = {"type": "video", "file_id": "ABC123"}
    items = [{"category": "Serie", "name": "Lost", "description": "Misterio en isla"}]

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="Hablamos de Lost"),
            patch("src.main.extract_data", return_value=items),
        ):
            _run(parsed, md, tmpdir)

        with open(os.path.join(md["vault_inbox_dir"], "Series y Películas.md")) as f:
            summary = f.read()
        assert "Lost" in summary
        assert "video reenviado sin enlace" in summary
        name, _ = _only_file(os.path.join(md["vault_inbox_dir"], PROCESSED_DIR))
        assert "telegram" in name


def test_process_urls_from_file():
    from src.main import process_urls

    items = [{"category": "Software", "name": "Cursor", "description": "Editor con IA"}]

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        urls_file = os.path.join(tmpdir, "urls.txt")
        with open(urls_file, "w", encoding="utf-8") as f:
            f.write(
                "https://www.tiktok.com/@user/video/1\n"
                "\n"
                "# comentario\n"
                "https://youtu.be/abc\n"
            )
        config = {
            "telegram": {"bot_token": "TOKEN", "offset_file": os.path.join(tmpdir, "offset.txt")},
            "whisper": {"model": "medium"},
            "llm": LLM_CONFIG,
            "markdown": md,
            "categories": CATEGORIES,
        }

        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4") as mock_dl,
            patch("src.main.transcribe", return_value="Hablamos de Cursor"),
            patch("src.main.extract_data", return_value=items),
        ):
            count = process_urls(config, urls_file)

        assert count == 2
        assert mock_dl.call_count == 2
        with open(os.path.join(md["vault_inbox_dir"], "Software.md"), encoding="utf-8") as f:
            content = f.read()
        assert "https://www.tiktok.com/@user/video/1" in content
        assert "https://youtu.be/abc" in content
        processed = os.listdir(os.path.join(md["vault_inbox_dir"], PROCESSED_DIR))
        assert len(processed) == 2


def test_process_urls_continues_after_failure():
    from src.main import process_urls

    items = [{"category": "Software", "name": "Zed", "description": "Editor"}]

    def mock_download(parsed, tmp_dir, bot_token, max_duration_seconds=None):
        if "malo" in parsed["url"]:
            raise RuntimeError("download failed")
        return "/tmp/fake.mp4"

    with tempfile.TemporaryDirectory() as tmpdir:
        md = _markdown_config(tmpdir)
        urls_file = os.path.join(tmpdir, "urls.txt")
        with open(urls_file, "w", encoding="utf-8") as f:
            f.write("https://youtu.be/malo\nhttps://youtu.be/bueno\n")
        config = {
            "telegram": {"bot_token": "TOKEN", "offset_file": os.path.join(tmpdir, "offset.txt")},
            "whisper": {"model": "medium"},
            "llm": LLM_CONFIG,
            "markdown": md,
            "categories": CATEGORIES,
        }

        with (
            patch("src.main.download_video", side_effect=mock_download),
            patch("src.main.transcribe", return_value="Hablamos de Zed"),
            patch("src.main.extract_data", return_value=items),
        ):
            count = process_urls(config, urls_file)

        assert count == 1
        with open(os.path.join(md["vault_inbox_dir"], "Software.md"), encoding="utf-8") as f:
            assert "https://youtu.be/bueno" in f.read()
