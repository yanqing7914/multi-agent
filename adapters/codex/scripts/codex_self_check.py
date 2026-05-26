#!/usr/bin/env python3
"""Codex adapter bridge contract self-check (does not spawn codex CLI)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent.parent / "_shared"
sys.path.insert(0, str(SHARED))

from self_check import run_adapter_self_check  # noqa: E402

if __name__ == "__main__":
    adapter_root = Path(__file__).resolve().parent.parent
    code = run_adapter_self_check(adapter_root, "codex", "launch_codex_worker.sh", ["QUICKSTART.md"])
    if code != 0:
        raise SystemExit(code)
    from worker_outcome import evaluate_worker_outcome  # noqa: E402

    fixtures = SHARED / "fixtures"
    stub_md = fixtures / "_codex_selfcheck_stub.md"
    stub_md.write_text("x" * 64, encoding="utf-8")
    try:
        ok, err, _ = evaluate_worker_outcome(
            pipeline_returncode=0,
            result_md=stub_md,
            result_json=fixtures / "_codex_missing.json",
            json_extracted=False,
            log_text='{"task_id":"T","role":"worker"}\n',
            require_json_file=True,
        )
        if ok or err != "missing_result_json":
            print(json.dumps({"ok": False, "error": f"codex json gate: ok={ok} err={err}"}, indent=2))
            raise SystemExit(1)
    finally:
        stub_md.unlink(missing_ok=True)
    print(json.dumps({"ok": True, "adapter": "codex", "outcome_fixtures": "pass"}, indent=2))
    raise SystemExit(0)
