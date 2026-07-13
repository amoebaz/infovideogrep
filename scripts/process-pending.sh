#!/usr/bin/env bash
# Procesa con Claude las transcripciones pendientes del vault (ver docs/cowork-task.md).
# Pensado para crontab: 17 */6 * * * /mnt/e/__DEV__/infovideogrep/scripts/process-pending.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_BIN="/home/lolo/.npm-global/bin/claude"
VAULT_DIR="$(grep '^VIDEOINBOX_DIR=' "$REPO/.env" | cut -d= -f2-)"
LOG="$REPO/data/cowork.log"

mkdir -p "$REPO/data"

# Si no hay pendientes, no gastamos una invocación de Claude.
if ! ls "$VAULT_DIR/Pendientes/"*.md >/dev/null 2>&1; then
    echo "=== $(date -Is) sin pendientes ===" >> "$LOG"
    exit 0
fi

{
    echo "=== $(date -Is) ==="
    cd "$REPO"
    "$CLAUDE_BIN" \
        -p "$(cat "$REPO/docs/cowork-task.md")" \
        --add-dir "$VAULT_DIR" \
        --permission-mode acceptEdits \
        --model sonnet \
        --output-format json < /dev/null
} >> "$LOG" 2>&1
