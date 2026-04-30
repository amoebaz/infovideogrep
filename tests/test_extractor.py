import json
from unittest.mock import patch, MagicMock
from src.extractor import extract_data, build_system_prompt


CATEGORY_NAMES = ["Software", "Serie", "Película", "Música", "Otro"]


def test_build_system_prompt_includes_categories():
    prompt = build_system_prompt(["Software", "Libro", "Lugar"])
    assert "Software" in prompt
    assert "Libro" in prompt
    assert "Lugar" in prompt
    assert "JSON" in prompt


def test_extract_data_returns_parsed_items():
    llm_response = json.dumps({
        "items": [
            {"category": "Software", "name": "Cursor", "description": "Editor de código con IA integrada"},
            {"category": "Serie", "name": "Severance", "description": "Thriller psicológico en Apple TV+"},
        ]
    })

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = llm_response
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    with patch("src.extractor._get_client", return_value=mock_client):
        result = extract_data(
            "En este video hablamos de Cursor un editor con IA y de Severance una serie de Apple TV+",
            llm_config={"base_url": "http://localhost:11434/v1", "api_key": "", "model": "llama3.1:8b"},
            category_names=CATEGORY_NAMES,
        )

    assert len(result) == 2
    assert result[0]["name"] == "Cursor"
    assert result[1]["category"] == "Serie"


def test_extract_data_empty_transcription():
    result_json = json.dumps({"items": []})

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = result_json
    mock_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    with patch("src.extractor._get_client", return_value=mock_client):
        result = extract_data(
            "",
            llm_config={"base_url": "http://localhost:11434/v1", "api_key": "", "model": "llama3.1:8b"},
            category_names=CATEGORY_NAMES,
        )
    assert result == []
