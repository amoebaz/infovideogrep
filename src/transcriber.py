from faster_whisper import WhisperModel

_model_cache: dict[str, WhisperModel] = {}


def _get_model(model_size: str) -> WhisperModel:
    if model_size not in _model_cache:
        _model_cache[model_size] = WhisperModel(
            model_size, device="cuda", compute_type="float16"
        )
    return _model_cache[model_size]


def transcribe(file_path: str, model_size: str = "medium") -> str:
    model = _get_model(model_size)
    segments, _ = model.transcribe(file_path)
    text = " ".join(seg.text.strip() for seg in segments)
    return text.strip()
