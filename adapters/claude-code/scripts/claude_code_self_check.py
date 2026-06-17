#!/usr/bin/env python3
"""Claude Code adapter bridge contract self-check (does not spawn claude CLI)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent.parent / "_shared"
sys.path.insert(0, str(SHARED))

from self_check import run_adapter_self_check  # noqa: E402

if __name__ == "__main__":
    adapter_root = Path(__file__).resolve().parent.parent
    code = run_adapter_self_check(
        adapter_root, "claude-code", "launch_claude_worker.sh", ["QUICKSTART.md"]
    )
    if code != 0:
        raise SystemExit(code)
    desktop_script = adapter_root / "scripts" / "prepare_claude_desktop.py"
    if not desktop_script.is_file():
        print(json.dumps({"ok": False, "error": "prepare_claude_desktop.py missing"}, indent=2))
        raise SystemExit(1)
    proc = subprocess.run([sys.executable, str(desktop_script), "--self-check"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "claude desktop self-check failed",
                    "output": (proc.stderr or proc.stdout or "").strip(),
                },
                indent=2,
            )
        )
        raise SystemExit(1)
    from worker_outcome import detect_log_error_mode  # noqa: E402

    quota_log = (SHARED / "fixtures" / "claude_429_budget.log").read_text(encoding="utf-8")
    mode = detect_log_error_mode(quota_log)
    if mode != "quota_exhausted":
        print(json.dumps({"ok": False, "error": f"quota detect: {mode}"}, indent=2))
        raise SystemExit(1)
    print(
        json.dumps(
            {
                "ok": True,
                "adapter": "claude-code",
                "quota_detection": "pass",
                "desktop_prompt": "pass",
            },
            indent=2,
        )
    )
    raise SystemExit(0)
