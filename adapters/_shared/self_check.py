#!/usr/bin/env python3
"""Common self-check helpers for thin client adapters (dependency-free)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from bridge import (
    CREATE_TASK_CARDS,
    MCP_SELF_CHECK,
    OPENCLAW_SCRIPTS,
    PANEL_SELF_CHECK,
    REPO_ROOT,
    RESULT_REPORT_TEMPLATE,
    TASK_CARD_TEMPLATE,
    VERIFY_WORKSPACE,
)
from worker_outcome import run_outcome_fixture_checks, run_dedup_self_check


def check_file(path: Path, executable: bool = False) -> str | None:
    if not path.exists():
        return f"missing file: {path}"
    if executable and not os.access(path, os.X_OK):
        return f"not executable: {path}"
    return None


def run_subprocess_self_check(script: Path, label: str) -> str | None:
    if not script.exists():
        return f"{label}: script missing ({script})"
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        snippet = (proc.stderr or proc.stdout or "").strip()[:400]
        return f"{label}: {snippet or 'failed'}"
    return None


def run_v2_v3_self_checks() -> list[str]:
    """Run MCP coordinator + IDE panel smoke tests (v2/v3)."""
    errors: list[str] = []
    for script, label in ((MCP_SELF_CHECK, "mcp-coordinator"), (PANEL_SELF_CHECK, "ide-panel")):
        err = run_subprocess_self_check(script, label)
        if err:
            errors.append(err)
    return errors


def run_adapter_self_check(
    adapter_root: Path,
    adapter_name: str,
    launcher_name: str,
    extra_docs: list[str] | None = None,
) -> int:
    errors: list[str] = []
    required_docs = ["SKILL.md", "README.md", *(extra_docs or [])]
    for name in required_docs:
        err = check_file(adapter_root / name)
        if err:
            errors.append(err)

    launcher = adapter_root / "scripts" / launcher_name
    err = check_file(launcher)
    if err:
        errors.append(err)

    examples = list((adapter_root / "examples").glob("*.yaml"))
    if not examples:
        errors.append(f"missing examples/*.yaml under {adapter_root}")

    for script in (VERIFY_WORKSPACE, CREATE_TASK_CARDS):
        err = check_file(script)
        if err:
            errors.append(err)

    for template in (RESULT_REPORT_TEMPLATE, TASK_CARD_TEMPLATE):
        err = check_file(template)
        if err:
            errors.append(err)

    errors.extend(run_outcome_fixture_checks())
    errors.extend(run_dedup_self_check())

    payload = {
        "ok": not errors,
        "adapter": adapter_name,
        "adapter_root": str(adapter_root),
        "repo_root": str(REPO_ROOT),
        "openclaw_scripts": str(OPENCLAW_SCRIPTS),
        "launcher": str(launcher),
        "examples": [str(p) for p in examples],
        "errors": errors,
    }
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


def main_template(adapter_name: str, launcher_name: str) -> None:
    adapter_root = Path(__file__).resolve().parent.parent / adapter_name
    raise SystemExit(run_adapter_self_check(adapter_root, adapter_name, launcher_name))
