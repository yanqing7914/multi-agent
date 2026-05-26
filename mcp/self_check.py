#!/usr/bin/env python3
"""MCP layer entrypoint for full_validate.sh."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "multi-agent-coordinator" / "scripts" / "self_check.py"

if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, str(SCRIPT)]))
