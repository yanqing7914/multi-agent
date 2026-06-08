#!/usr/bin/env bash
# Prepare a Codex Desktop worker prompt from a task card.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/prepare_desktop_worker.py" "$@"
