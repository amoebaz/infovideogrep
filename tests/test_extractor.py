import json
import pytest
from unittest.mock import patch, MagicMock
from src.extractor import extract_data, build_system_prompt, _parse_items


def test_parse_plain_json():
    content = '{"items": [{"category": "Software", "name": "Zed", "description": "Editor"}]}'
    assert _parse_items(content) == [
        {"category": "Software", "name": "Zed", "description": "Editor"}
    ]


def test_parse_json_wrapped_in_markdown_fence():
    content = (
        "```json\n"
        '{\n  "items": [\n'
        '    {"category": "Serie", "name": "Severance", "description": "Apple TV"}\n'
        "  ]\n}\n"
        "```"
    )
    assert _parse_items(content) == [
        {"category": "Serie", "name": "Severance", "description": "Apple TV"}
    ]


def test_parse_json_with_leading_prose():
    content = 'Aquí tienes:\n{"items": [{"category": "Otro", "name": "X", "description": "y"}]}'
    assert _parse_items(content) == [{"category": "Otro", "name": "X", "description": "y"}]


def test_parse_empty_items():
    assert _parse_items('{"items": []}') == []


def test_parse_garbage_raises_value_error():
    with pytest.raises(ValueError):
        _parse_items("lo siento, no puedo ayudarte")


def test_parse_none_or_empty_raises_value_error():
    with pytest.raises(ValueError):
        _parse_items("")
    with pytest.raises(ValueError):
        _parse_items(None)


def test_parse_invalid_json_raises_value_error():
    with pytest.raises(ValueError):
        _parse_items("{not valid json")


def test_parse_json_without_items_key_raises_value_error():
    with pytest.raises(ValueError):
        _parse_items('{"foo": "bar"}')


def test_parse_drops_invalid_items_but_keeps_valid_ones():
    content = json.dumps({
        "items": [
            {"category": "Software", "name": "Zed", "description": "Editor"},
            {"category": "Software", "name": "Sin descripción"},
            {"category": "Software", "name": "X", "description": ""},
            {"category": "Software", "name": "Y", "description": 123},
            "not a dict",
            {"category": "Serie", "name": "Severance", "description": "Apple TV"},
        ]
    })
    assert _parse_items(content) == [
        {"category": "Software", "name": "Zed", "description": "Editor"},
        {"category": "Serie", "name": "Severance", "description": "Apple TV"},
    ]


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
