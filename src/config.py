# src/config.py
import os
import re
from pathlib import Path

import yaml


REQUIRED_SECTIONS = ["telegram", "whisper", "llm", "markdown"]
_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _load_dotenv(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _expand(value):
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            if var_name not in os.environ:
                raise KeyError(f"Environment variable {var_name} is not set")
            return os.environ[var_name]
        return _VAR_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def load_config(path: str) -> dict:
    _load_dotenv()
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    for section in REQUIRED_SECTIONS:
        if section not in config:
            raise KeyError(f"Missing required config section: {section}")
    return _expand(config)
