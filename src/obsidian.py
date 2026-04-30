import os

CATEGORY_ICONS = {
    "Software": "🖥️",
    "Serie": "🎬",
    "Película": "🎬",
    "Música": "🎵",
}
DEFAULT_ICON = "📌"


def format_entry(items: list[dict], url: str, date_str: str, failed: bool = False) -> str:
    if failed or not items:
        return f"- ⚠️ **No se pudo transcribir**\n  [enlace al video]({url})\n"

    lines = []
    for item in items:
        icon = CATEGORY_ICONS.get(item["category"], DEFAULT_ICON)
        lines.append(
            f"- {icon} **{item['category']}**: {item['name']} — \"{item['description']}\"\n"
            f"  [enlace al video]({url})"
        )
    return "\n".join(lines) + "\n"


def append_to_inbox(inbox_path: str, entry: str, date_str: str) -> None:
    header = f"## {date_str}"

    # Read existing content
    content = ""
    if os.path.exists(inbox_path):
        with open(inbox_path, "r") as f:
            content = f.read()

    # If today's header already exists, append under it
    if header in content:
        # Find the position after the header line
        header_pos = content.index(header)
        # Find the next ## or end of file
        next_header = content.find("\n## ", header_pos + len(header))
        if next_header == -1:
            # Append at end of file
            content = content.rstrip() + "\n" + entry + "\n"
        else:
            # Insert before next header
            content = (
                content[:next_header].rstrip() + "\n" + entry + "\n" + content[next_header:]
            )
    else:
        # Add new date header at end
        if content:
            content = content.rstrip() + "\n\n"
        content += header + "\n\n" + entry + "\n"

    dirname = os.path.dirname(inbox_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    with open(inbox_path, "w") as f:
        f.write(content)
