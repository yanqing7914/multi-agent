#!/usr/bin/env python3
"""Project-wide adapter validation: OpenClaw + cursor/codex/claude-code (dependency-free)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    (
        "capture_changed_files",
        REPO_ROOT / "adapters" / "openclaw" / "scripts" / "capture_changed_files.py",
        ["--self-check"],
    ),
    ("native_skill_installer", REPO_ROOT / "scripts" / "install_native_skills.py", ["--self-check"]),
    ("pip-cli", REPO_ROOT / "multi_agent_coding" / "cli.py", ["self-check"]),
    ("release-package-verifier", REPO_ROOT / "scripts" / "verify_release_packages.py", ["--self-check"]),
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


def run_check(name: str, script: Path, extra_args: list[str]) -> dict:
    if not script.exists():
        return {"name": name, "script": str(script), "ok": False, "error": "script missing"}
    started = time.monotonic()
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
        "duration_s": round(time.monotonic() - started, 2),
    }
    if not ok:
        entry["output"] = (proc.stderr or proc.stdout or "").strip()[:500]
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    parser.add_argument(
        "--jobs",
        type=int,
        default=min(8, os.cpu_count() or 4),
        help="Parallel check processes (default: min(8, cpu_count)); use 1 for serial",
    )
    args = parser.parse_args()

    total = len(ADAPTER_CHECKS)
    results_by_name: dict[str, dict] = {}
    done = 0
    # Every self-check is hermetic (temp-dir state), so they can run in parallel.
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {
            pool.submit(run_check, name, script, extra_args): name
            for name, script, extra_args in ADAPTER_CHECKS
        }
        for future in as_completed(futures):
            entry = future.result()
            results_by_name[entry["name"]] = entry
            done += 1
            if not args.json:
                status = "PASS" if entry["ok"] else "FAIL"
                duration = entry.get("duration_s")
                suffix = f" ({duration}s)" if duration is not None else ""
                print(f"[{done}/{total}] [{status}] {entry['name']}{suffix}", flush=True)

    results = [results_by_name[name] for name, _script, _args in ADAPTER_CHECKS]
    errors = [
        f"{item['name']}: {item.get('output') or item.get('error') or 'failed'}"
        for item in results
        if not item["ok"]
    ]

    payload = {"ok": not errors, "checks": results, "errors": errors}
    if args.json:
        print(json.dumps(payload, indent=2))
    elif errors:
        print("\nFailures:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
