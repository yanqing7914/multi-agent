#!/usr/bin/env python3
"""Discover and run pytest / npm test / pnpm test (dependency-free wrapper)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from _tool_base import (
    command_is_allowed,
    command_is_blocked,
    emit_json,
    load_json_input,
    resolve_repo_root,
    tool_result,
)


def _which(name: str) -> str | None:
    from shutil import which

    return which(name)


def discover(repo_root: Path) -> dict:
    runners: list[dict] = []
    package_json = repo_root / "package.json"
    if package_json.exists():
        try:
            pkg = json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pkg = {}
        scripts = pkg.get("scripts") or {}
        if "test" in scripts:
            if _which("pnpm"):
                runners.append({"runner": "pnpm", "command": "pnpm test", "kind": "node"})
            if _which("npm"):
                runners.append({"runner": "npm", "command": "npm test", "kind": "node"})

    pytest_markers = [
        repo_root / "pytest.ini",
        repo_root / "pyproject.toml",
        repo_root / "setup.cfg",
        repo_root / "tox.ini",
    ]
    has_pytest_files = any(repo_root.rglob("test_*.py")) or any(repo_root.rglob("*_test.py"))
    if has_pytest_files or any(p.exists() for p in pytest_markers):
        if _which("pytest") or _which("python3"):
            cmd = "pytest" if _which("pytest") else "python3 -m pytest"
            runners.append({"runner": "pytest", "command": cmd, "kind": "python"})

    return tool_result(True, action="discover", runners=runners, count=len(runners))


def run_tests(repo_root: Path, runner: str | None, command: str | None, allowed_commands: list[str] | None, blocked_commands: list[str] | None) -> dict:
    discovered = discover(repo_root)
    selected = None
    if command:
        selected = {"runner": runner or "custom", "command": command}
    elif runner:
        for item in discovered.get("runners", []):
            if item["runner"] == runner:
                selected = item
                break
    elif discovered.get("runners"):
        selected = discovered["runners"][0]

    if not selected:
        return tool_result(False, action="run", error="no test runner discovered; pass --command explicitly")

    cmd_text = selected["command"]
    if command_is_blocked(cmd_text, blocked_commands):
        return tool_result(False, action="run", error=f"blocked command: {cmd_text}")
    if allowed_commands and not command_is_allowed(cmd_text, allowed_commands):
        return tool_result(False, action="run", error=f"command not in allowlist: {cmd_text}")

    proc = subprocess.run(
        cmd_text,
        shell=True,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return tool_result(
        proc.returncode == 0,
        action="run",
        runner=selected.get("runner"),
        command=cmd_text,
        returncode=proc.returncode,
        stdout=proc.stdout[-8000:],
        stderr=proc.stderr[-8000:],
    )


def invoke(payload: dict) -> dict:
    action = payload.get("action", "discover")
    repo_root = resolve_repo_root(payload.get("repo_root"))
    if action == "discover":
        return discover(repo_root)
    if action == "run":
        return run_tests(
            repo_root,
            payload.get("runner"),
            payload.get("command"),
            payload.get("allowed_commands"),
            payload.get("blocked_commands"),
        )
    return tool_result(False, error=f"unknown action: {action}")


def run_self_check() -> int:
    errors: list[str] = []
    repo_root = Path(__file__).resolve().parent.parent
    discovered = discover(repo_root)
    if not discovered.get("ok"):
        errors.append("discover failed")
    payload = invoke({"action": "discover", "repo_root": str(repo_root)})
    if not payload.get("ok"):
        errors.append("invoke discover failed")
    if errors:
        emit_json({"ok": False, "errors": errors})
        return 1
    emit_json({"ok": True, "message": "test_runner_tool self-check passed", "runners": discovered.get("runners", [])})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("discover", "run"), default="discover")
    parser.add_argument("--repo-root")
    parser.add_argument("--runner", help="pytest | npm | pnpm")
    parser.add_argument("--command", help="Explicit test command")
    parser.add_argument("--json-in")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    if args.json_in is not None or not sys.stdin.isatty():
        result = invoke(load_json_input(args.json_in))
        emit_json(result)
        return 0 if result.get("ok") else 1

    result = invoke(
        {
            "action": args.action,
            "repo_root": args.repo_root,
            "runner": args.runner,
            "command": args.command,
        }
    )
    emit_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
