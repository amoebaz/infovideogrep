import os
import tempfile
from unittest.mock import patch
from src.main import process_message
from src.downloader import DurationExceeded


CATEGORIES = [
    {"name": "Software", "icon": "🖥️"},
    {"name": "Serie", "icon": "📺"},
    {"name": "Película", "icon": "🎬"},
]


def test_process_message_url_full_pipeline():
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/123"}
    llm_config = {"base_url": "http://localhost:11434/v1", "api_key": "", "model": "test"}
    items = [{"category": "Software", "name": "Cursor", "description": "Editor con IA"}]

    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_path = os.path.join(tmpdir, "VideoInbox.md")

        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4") as mock_dl,
            patch("src.main.transcribe", return_value="Hablamos de Cursor") as mock_tr,
            patch("src.main.extract_data", return_value=items) as mock_ex,
        ):
            process_message(
                parsed=parsed,
                bot_token="TOKEN",
                whisper_model="medium",
                llm_config=llm_config,
                inbox_path=inbox_path,
                tmp_dir=tmpdir,
                categories=CATEGORIES,
            )

            mock_dl.assert_called_once()
            mock_tr.assert_called_once()
            mock_ex.assert_called_once()

        with open(inbox_path, "r") as f:
            content = f.read()
        assert "Cursor" in content


def test_process_message_failed_transcription():
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/456"}
    llm_config = {"base_url": "http://localhost:11434/v1", "api_key": "", "model": "test"}

    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_path = os.path.join(tmpdir, "VideoInbox.md")

        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value=""),
        ):
            process_message(
                parsed=parsed,
                bot_token="TOKEN",
                whisper_model="medium",
                llm_config=llm_config,
                inbox_path=inbox_path,
                tmp_dir=tmpdir,
                categories=CATEGORIES,
            )

        with open(inbox_path, "r") as f:
            content = f.read()
        assert "no se pudo transcribir" in content.lower()


def test_process_message_llm_all_fail_no_fallback():
    """LLM fails twice, no fallback configured — raw transcription saved."""
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/789"}
    llm_config = {"base_url": "http://localhost:11434/v1", "api_key": "", "model": "test"}

    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_path = os.path.join(tmpdir, "VideoInbox.md")

        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="Hablamos de algo interesante"),
            patch("src.main.extract_data", side_effect=Exception("LLM down")),
        ):
            process_message(
                parsed=parsed,
                bot_token="TOKEN",
                whisper_model="medium",
                llm_config=llm_config,
                inbox_path=inbox_path,
                tmp_dir=tmpdir,
                categories=CATEGORIES,
            )

        with open(inbox_path, "r") as f:
            content = f.read()
        assert "transcripción sin procesar" in content.lower()
        assert "Hablamos de algo interesante" in content


def test_process_message_fallback_llm_succeeds():
    """Primary LLM fails twice, fallback LLM succeeds."""
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
        inbox_path = os.path.join(tmpdir, "VideoInbox.md")

        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="Hablamos de Neovim"),
            patch("src.main.extract_data", side_effect=mock_extract),
            patch("src.main._ensure_ollama_running"),
        ):
            process_message(
                parsed=parsed,
                bot_token="TOKEN",
                whisper_model="medium",
                llm_config=llm_config,
                inbox_path=inbox_path,
                tmp_dir=tmpdir,
                categories=CATEGORIES,
                llm_fallback_config=fallback_config,
            )

        with open(inbox_path, "r") as f:
            content = f.read()
        assert "Neovim" in content
        assert "transcripción sin procesar" not in content.lower()


def test_process_message_llm_succeeds_on_retry():
    """LLM fails first attempt, succeeds on second."""
    parsed = {"type": "url", "url": "https://www.tiktok.com/@user/video/101"}
    llm_config = {"base_url": "http://localhost:11434/v1", "api_key": "", "model": "test"}
    items = [{"category": "Software", "name": "Docker", "description": "Contenedores"}]

    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_path = os.path.join(tmpdir, "VideoInbox.md")

        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="Hablamos de Docker"),
            patch("src.main.extract_data", side_effect=[Exception("timeout"), items]),
        ):
            process_message(
                parsed=parsed,
                bot_token="TOKEN",
                whisper_model="medium",
                llm_config=llm_config,
                inbox_path=inbox_path,
                tmp_dir=tmpdir,
                categories=CATEGORIES,
            )

        with open(inbox_path, "r") as f:
            content = f.read()
        assert "Docker" in content
        assert "transcripción sin procesar" not in content.lower()


def test_process_message_duration_exceeded_writes_warning():
    """Long video raises DurationExceeded → friendly inbox entry, no transcription."""
    parsed = {"type": "url", "url": "https://www.youtube.com/watch?v=longone"}
    llm_config = {"base_url": "http://localhost:11434/v1", "api_key": "", "model": "test"}

    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_path = os.path.join(tmpdir, "VideoInbox.md")

        with (
            patch("src.main.download_video", side_effect=DurationExceeded(7200, 3600)),
            patch("src.main.transcribe") as mock_tr,
        ):
            process_message(
                parsed=parsed,
                bot_token="TOKEN",
                whisper_model="medium",
                llm_config=llm_config,
                inbox_path=inbox_path,
                tmp_dir=tmpdir,
                categories=CATEGORIES,
                max_duration_seconds=3600,
            )
            mock_tr.assert_not_called()

        with open(inbox_path, "r") as f:
            content = f.read()
        assert "Duración excedida" in content
        assert "120 min" in content  # 7200s = 120 min
        assert "60 min" in content   # 3600s = 60 min


def test_process_message_forwarded_video_no_url():
    """Forwarded video has no source URL — should use fallback text."""
    parsed = {"type": "video", "file_id": "ABC123"}
    llm_config = {"base_url": "http://localhost:11434/v1", "api_key": "", "model": "test"}
    items = [{"category": "Serie", "name": "Lost", "description": "Misterio en isla"}]

    with tempfile.TemporaryDirectory() as tmpdir:
        inbox_path = os.path.join(tmpdir, "VideoInbox.md")

        with (
            patch("src.main.download_video", return_value="/tmp/fake.mp4"),
            patch("src.main.transcribe", return_value="Hablamos de Lost"),
            patch("src.main.extract_data", return_value=items),
        ):
            process_message(
                parsed=parsed,
                bot_token="TOKEN",
                whisper_model="medium",
                llm_config=llm_config,
                inbox_path=inbox_path,
                tmp_dir=tmpdir,
                categories=CATEGORIES,
            )

        with open(inbox_path, "r") as f:
            content = f.read()
        assert "Lost" in content
        assert "video reenviado sin enlace" in content
