#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
PIPELINE_PYTHON="${KNOWLEDGE_OS_TELEGRAM_PYTHON:-$HOME/.local/share/knowledge-os/telegram-venv/bin/python}"
export PYTHONPATH="$PWD/src"
export PYTHONPYCACHEPREFIX="$HOME/.cache/knowledge-os/pycache"
exec "$PIPELINE_PYTHON" -m knowledge_os.notion_pipeline "$@"
