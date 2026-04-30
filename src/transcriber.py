from faster_whisper import WhisperModel

_model_cache: dict[str, WhisperModel] = {}


def _get_model(model_size: str, device: str, compute_type: str) -> WhisperModel:
    cache_key = f"{model_size}|{device}|{compute_type}"
    if cache_key not in _model_cache:
        _model_cache[cache_key] = WhisperModel(
            model_size, device=device, compute_type=compute_type
        )
    return _model_cache[cache_key]


def transcribe(
    file_path: str,
    model_size: str = "medium",
    device: str = "cpu",
    compute_type: str = "int8",
) -> str:
    model = _get_model(model_size, device, compute_type)
    segments, _ = model.transcribe(file_path)
    text = " ".join(seg.text.strip() for seg in segments)
    return text.strip()
