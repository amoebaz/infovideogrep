from unittest.mock import patch, MagicMock
from src.transcriber import transcribe


def test_transcribe_returns_text():
    mock_segment = MagicMock()
    mock_segment.text = " Hola esto es una prueba"

    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], None)

    with patch("src.transcriber._get_model", return_value=mock_model):
        result = transcribe("/fake/video.mp4", model_size="medium")
    assert result == "Hola esto es una prueba"


def test_transcribe_empty_audio_returns_empty():
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([], None)

    with patch("src.transcriber._get_model", return_value=mock_model):
        result = transcribe("/fake/video.mp4", model_size="medium")
    assert result == ""
