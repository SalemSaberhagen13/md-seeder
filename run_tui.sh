#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TUI_DIR="$SCRIPT_DIR/tui"
VENV_DIR="$TUI_DIR/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c "import textual" &>/dev/null; then
    echo "Installing dependencies into $VENV_DIR..."
    "$VENV_DIR/bin/pip" install --quiet -r "$TUI_DIR/requirements.txt"
fi

exec "$VENV_DIR/bin/python" "$TUI_DIR/app.py" "$@"
