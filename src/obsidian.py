import os
import re
from datetime import datetime

DEFAULT_ICON = "📌"

PENDING_DIR = "Pendientes"
PROCESSED_DIR = "Procesadas"

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_PENDING_STATES = ("pendiente", "error_llm")


def _sanitize_filename(text: str) -> str:
    cleaned = _INVALID_FILENAME_CHARS.sub("", text).strip()
    return cleaned or "video"


def _unique_path(directory: str, filename: str) -> str:
    base, ext = os.path.splitext(filename)
    path = os.path.join(directory, filename)
    counter = 2
    while os.path.exists(path):
        path = os.path.join(directory, f"{base} ({counter}){ext}")
        counter += 1
    return path


def save_transcription(
    vault_dir: str,
    *,
    url: str,
    text: str,
    dt: datetime,
    slug: str,
    estado: str = "pendiente",
    intentos: int = 0,
) -> str:
    subdir = PENDING_DIR if estado in _PENDING_STATES else PROCESSED_DIR
    directory = os.path.join(vault_dir, subdir)
    os.makedirs(directory, exist_ok=True)
    filename = f"{dt:%Y-%m-%d %H-%M} - {_sanitize_filename(slug)}.md"
    path = _unique_path(directory, filename)

    content = (
        "---\n"
        f"fecha: {dt.isoformat(timespec='seconds')}\n"
        f"url: {url}\n"
        f"estado: {estado}\n"
        f"intentos: {intentos}\n"
        "---\n\n"
        "# Transcripción\n\n"
        f"{text.strip()}\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def update_estado(path: str, estado: str, intentos: int | None = None) -> None:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    frontmatter_end = content.index("\n---") + 1
    frontmatter = content[:frontmatter_end]
    frontmatter = re.sub(r"(?m)^estado: .*$", f"estado: {estado}", frontmatter, count=1)
    if intentos is not None:
        frontmatter = re.sub(r"(?m)^intentos: .*$", f"intentos: {intentos}", frontmatter, count=1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(frontmatter + content[frontmatter_end:])


def mark_processed(path: str, vault_dir: str) -> str:
    update_estado(path, "procesada")
    processed_dir = os.path.join(vault_dir, PROCESSED_DIR)
    os.makedirs(processed_dir, exist_ok=True)
    dest = _unique_path(processed_dir, os.path.basename(path))
    os.replace(path, dest)
    return dest


def format_entry(
    items: list[dict],
    url: str,
    date_str: str,
    category_icons: dict[str, str],
    failed: bool = False,
) -> str:
    if failed or not items:
        return f"- ⚠️ **No se pudo transcribir**\n  [enlace al video]({url})\n"

    lines = []
    for item in items:
        icon = category_icons.get(item["category"], DEFAULT_ICON)
        lines.append(
            f"- {icon} **{item['category']}**: {item['name']} — \"{item['description']}\"\n"
            f"  [enlace al video]({url})"
        )
    return "\n".join(lines) + "\n"


def route_items(
    items: list[dict],
    summary_files: list[dict],
    default_file: str,
) -> dict[str, list[dict]]:
    category_to_file = {
        category: entry["file"]
        for entry in summary_files
        for category in entry["categories"]
    }
    routed: dict[str, list[dict]] = {}
    for item in items:
        filename = category_to_file.get(item.get("category"), default_file)
        routed.setdefault(filename, []).append(item)
    return routed


def append_to_markdown(path: str, entry: str, date_str: str) -> None:
    header = f"## {date_str}"

    content = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

    if header in content:
        header_pos = content.index(header)
        next_header = content.find("\n## ", header_pos + len(header))
        if next_header == -1:
            content = content.rstrip() + "\n" + entry + "\n"
        else:
            content = (
                content[:next_header].rstrip() + "\n" + entry + "\n" + content[next_header:]
            )
    else:
        if content:
            content = content.rstrip() + "\n\n"
        content += header + "\n\n" + entry + "\n"

    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
