#!/usr/bin/env bash
# Minimal Codex worker launcher — delegates to Python bridge (dependency-free).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/launch_codex_worker.py" "$@"
