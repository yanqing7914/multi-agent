#!/usr/bin/env python3
"""Project-wide adapter validation: OpenClaw + cursor/codex/claude-code (dependency-free)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ADAPTER_CHECKS = [
    ("openclaw", REPO_ROOT / "adapters" / "openclaw" / "scripts" / "validate_all.py", []),
    ("cursor", REPO_ROOT / "adapters" / "cursor" / "scripts" / "cursor_self_check.py", []),
    ("codex", REPO_ROOT / "adapters" / "codex" / "scripts" / "codex_self_check.py", []),
    ("codex-doctor", REPO_ROOT / "adapters" / "codex" / "scripts" / "doctor_codex.py", ["--self-check"]),
    ("codex-native-plan", REPO_ROOT / "adapters" / "codex" / "scripts" / "prepare_native_plan.py", ["--self-check"]),
    ("codex-app-dogfood", REPO_ROOT / "adapters" / "codex" / "scripts" / "dogfood_codex_app.py", ["--self-check"]),
    ("codex-finalize-native", REPO_ROOT / "adapters" / "codex" / "scripts" / "finalize_native_run.py", ["--self-check"]),
    ("run-multi-agent", REPO_ROOT / "scripts" / "run_multi_agent.py", ["--self-check"]),
    (
        "claude-code",
        REPO_ROOT / "adapters" / "claude-code" / "scripts" / "claude_code_self_check.py",
        [],
    ),
    ("mcp-coordinator", REPO_ROOT / "mcp" / "multi-agent-coordinator" / "scripts" / "self_check.py", []),
    ("ide-panel", REPO_ROOT / "ide" / "multi-agent-panel" / "scripts" / "self_check.py", []),
    ("panel-launcher", REPO_ROOT / "ide" / "multi-agent-panel" / "scripts" / "open_panel.py", ["--self-check"]),
    ("bench", REPO_ROOT / "bench" / "run_bench.py", ["--self-check", "--dry-runtime"]),
    ("git_tool", REPO_ROOT / "tools" / "git_tool.py", ["--self-check"]),
    ("test_runner_tool", REPO_ROOT / "tools" / "test_runner_tool.py", ["--self-check"]),
    ("lint_tool", REPO_ROOT / "tools" / "lint_tool.py", ["--self-check"]),
    ("shell_tool", REPO_ROOT / "tools" / "shell_tool.py", ["--self-check"]),
    ("repo_index_tool", REPO_ROOT / "tools" / "repo_index_tool.py", ["--self-check"]),
    ("worktree_tool", REPO_ROOT / "tools" / "worktree_tool.py", ["--self-check"]),
    ("run_graph", REPO_ROOT / "adapters" / "openclaw" / "scripts" / "run_graph.py", ["--self-check"]),
    ("native_skill_installer", REPO_ROOT / "scripts" / "install_native_skills.py", ["--self-check"]),
    ("doctor", REPO_ROOT / "scripts" / "doctor.py", ["--self-check"]),
    ("configure_mcp", REPO_ROOT / "scripts" / "configure_mcp.py", ["--self-check"]),
    ("hermes", REPO_ROOT / "adapters" / "hermes" / "scripts" / "hermes_self_check.py", ["--self-check"]),
    ("run_loop", REPO_ROOT / "adapters" / "openclaw" / "scripts" / "run_loop.py", ["--self-check"]),
    ("cursor-sdk", REPO_ROOT / "adapters" / "cursor" / "scripts" / "prepare_cursor_sdk.py", ["--self-check"]),
    ("mcp-serve", REPO_ROOT / "mcp" / "multi-agent-coordinator" / "scripts" / "serve.py", ["--self-check"]),
    ("memory_log", REPO_ROOT / "adapters" / "openclaw" / "scripts" / "memory_log.py", ["--self-check"]),
    (
        "dogfood_claude",
        REPO_ROOT / "adapters" / "claude-code" / "scripts" / "dogfood_claude.py",
        ["--self-check"],
    ),
    (
        "swebench-lite",
        REPO_ROOT / "bench" / "swebench-lite" / "run_swebench_lite.py",
        ["--self-check"],
    ),
    (
        "memory_rotate",
        REPO_ROOT / "adapters" / "openclaw" / "scripts" / "memory_rotate.py",
        ["--self-check"],
    ),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = parser.parse_args()

    results: list[dict] = []
    errors: list[str] = []

    for name, script, extra_args in ADAPTER_CHECKS:
        if not script.exists():
            entry = {"name": name, "script": str(script), "ok": False, "error": "script missing"}
            errors.append(f"{name}: script missing")
            results.append(entry)
            continue
        proc = subprocess.run(
            [sys.executable, str(script), *extra_args],
            capture_output=True,
            text=True,
            check=False,
        )
        ok = proc.returncode == 0
        entry = {
            "name": name,
            "script": str(script),
            "ok": ok,
            "returncode": proc.returncode,
        }
        if not ok:
            snippet = (proc.stderr or proc.stdout or "").strip()[:500]
            entry["output"] = snippet
            errors.append(f"{name}: {snippet or 'failed'}")
        results.append(entry)

    payload = {"ok": not errors, "checks": results, "errors": errors}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for item in results:
            status = "PASS" if item["ok"] else "FAIL"
            print(f"[{status}] {item['name']}")
        if errors:
            print("\nFailures:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
