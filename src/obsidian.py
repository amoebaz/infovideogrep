import os

DEFAULT_ICON = "📌"


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


def append_to_inbox(inbox_path: str, entry: str, date_str: str) -> None:
    header = f"## {date_str}"

    content = ""
    if os.path.exists(inbox_path):
        with open(inbox_path, "r") as f:
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

    dirname = os.path.dirname(inbox_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(inbox_path, "w") as f:
        f.write(content)
