#!/usr/bin/env python3
"""Cursor adapter bridge contract self-check (does not spawn agent CLI)."""

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
    code = run_adapter_self_check(adapter_root, "cursor", "launch_cursor_worker.sh", ["QUICKSTART.md"])
    if code != 0:
        raise SystemExit(code)
    desktop_script = adapter_root / "scripts" / "prepare_cursor_desktop.py"
    if not desktop_script.is_file():
        print(json.dumps({"ok": False, "error": "prepare_cursor_desktop.py missing"}, indent=2))
        raise SystemExit(1)
    proc = subprocess.run([sys.executable, str(desktop_script), "--self-check"], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "cursor desktop self-check failed",
                    "output": (proc.stderr or proc.stdout or "").strip(),
                },
                indent=2,
            )
        )
        raise SystemExit(1)
    from worker_outcome import evaluate_worker_outcome  # noqa: E402

    tee_log = (SHARED / "fixtures" / "tee_ok_cli_failed.log").read_text(encoding="utf-8")
    ok, err, _ = evaluate_worker_outcome(
        pipeline_returncode=0,
        result_md=SHARED / "fixtures" / "nonexistent.md",
        result_json=SHARED / "fixtures" / "nonexistent.json",
        json_extracted=False,
        log_text=tee_log,
    )
    if ok or err != "quota_exhausted":
        print(json.dumps({"ok": False, "error": f"tee fixture: ok={ok} err={err}"}, indent=2))
        raise SystemExit(1)
    print(json.dumps({"ok": True, "adapter": "cursor", "tee_fixture": "pass", "desktop_prompt": "pass"}, indent=2))
    raise SystemExit(0)
