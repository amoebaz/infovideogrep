#!/usr/bin/env bash
# Procesa con Claude las transcripciones pendientes del vault (ver docs/cowork-task.md).
# Pensado para crontab: 17 */6 * * * /mnt/e/__DEV__/infovideogrep/scripts/process-pending.sh
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_BIN="/home/lolo/.npm-global/bin/claude"
LOG="$REPO/data/cowork.log"

# Extrae VIDEOINBOX_DIR de .env sin dejar que un grep sin coincidencia
# (set -e) mate el script antes de poder loguear el error.
VAULT_DIR="$(grep '^VIDEOINBOX_DIR=' "$REPO/.env" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
# Quita CR final (ficheros .env con CRLF) y comillas envolventes, simples o dobles.
VAULT_DIR="${VAULT_DIR%$'\r'}"
VAULT_DIR="${VAULT_DIR%\"}"
VAULT_DIR="${VAULT_DIR#\"}"
VAULT_DIR="${VAULT_DIR%\'}"
VAULT_DIR="${VAULT_DIR#\'}"

mkdir -p "$REPO/data"

if [[ -z "$VAULT_DIR" || ! -d "$VAULT_DIR" ]]; then
    echo "=== $(date -Is) ERROR: VIDEOINBOX_DIR inválido: '$VAULT_DIR' ===" >> "$LOG"
    exit 1
fi

# Si no hay pendientes, no gastamos una invocación de Claude.
if ! ls "$VAULT_DIR/Pendientes/"*.md >/dev/null 2>&1; then
    echo "=== $(date -Is) sin pendientes ===" >> "$LOG"
    exit 0
fi

# Claude no necesita abrir .env: le pasamos la carpeta del vault ya resuelta.
PROMPT="$(cat "$REPO/docs/cowork-task.md")

La carpeta del vault (VIDEOINBOX_DIR) es: $VAULT_DIR"

{
    echo "=== $(date -Is) ==="
    cd "$REPO"
    "$CLAUDE_BIN" \
        -p "$PROMPT" \
        --add-dir "$VAULT_DIR" \
        --permission-mode acceptEdits \
        --model sonnet \
        --output-format json < /dev/null
} >> "$LOG" 2>&1
