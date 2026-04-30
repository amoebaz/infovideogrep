# tests/test_config.py
import os
import tempfile
import pytest
from src.config import load_config


def test_load_config_returns_all_sections():
    config_content = """
telegram:
  bot_token: "TEST_TOKEN"
  offset_file: "./data/offset.txt"
whisper:
  model: "medium"
llm:
  base_url: "http://localhost:11434/v1"
  api_key: ""
  model: "llama3.1:8b"
markdown:
  inbox_path: "./output/VideoInbox.md"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config = load_config(f.name)

    assert config["telegram"]["bot_token"] == "TEST_TOKEN"
    assert config["whisper"]["model"] == "medium"
    assert config["llm"]["base_url"] == "http://localhost:11434/v1"
    assert config["markdown"]["inbox_path"] == "./output/VideoInbox.md"
    os.unlink(f.name)


def test_load_config_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")


def test_load_config_missing_section_raises():
    config_content = """
telegram:
  bot_token: "TEST_TOKEN"
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        with pytest.raises(KeyError):
            load_config(f.name)
    os.unlink(f.name)
