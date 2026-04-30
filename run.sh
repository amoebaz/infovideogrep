#!/usr/bin/env bash
# InfoVideoGrep — run script
# Usage:
#   ./run.sh              Single run: process pending messages and exit
#   ./run.sh --watch      Watch mode: poll every 60s (Ctrl+C to stop)
#   ./run.sh --watch 30   Watch mode: poll every 30s
#   ./run.sh --help       Show all options

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Use venv if available
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python -m src.main "$@"
