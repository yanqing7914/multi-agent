#!/usr/bin/env python3
"""Sandboxed shell runner with allowlist/denylist (dependency-free)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from _tool_base import (
    DEFAULT_BLOCKED_COMMANDS,
    command_is_allowed,
    command_is_blocked,
    emit_json,
    load_json_input,
    resolve_repo_root,
    tool_result,
    validate_path_scope,
)


def run_shell(payload: dict) -> dict:
    command = payload.get("command", "").strip()
    if not command:
        return tool_result(False, error="command is required")

    blocked = payload.get("blocked_commands") or DEFAULT_BLOCKED_COMMANDS
    allowed = payload.get("allowed_commands")
    if command_is_blocked(command, blocked):
        return tool_result(False, error=f"blocked command: {command}")
    if allowed and not command_is_allowed(command, allowed):
        return tool_result(False, error=f"command not in allowlist: {command}")

    repo_root = resolve_repo_root(payload.get("repo_root") or payload.get("cwd"))
    cwd = payload.get("cwd")
    workdir = Path(cwd).expanduser().resolve() if cwd else repo_root
    ok, reason = validate_path_scope(str(workdir), repo_root, payload.get("allowed_paths"), payload.get("blocked_paths"))
    if not ok:
        return tool_result(False, error=f"cwd scope rejected: {reason}")

    timeout = int(payload.get("timeout", 120))
    proc = subprocess.run(
        command,
        shell=True,
        cwd=str(workdir),
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    return tool_result(
        proc.returncode == 0,
        command=command,
        cwd=str(workdir),
        returncode=proc.returncode,
        stdout=proc.stdout[-8000:],
        stderr=proc.stderr[-8000:],
    )


def run_self_check() -> int:
    errors: list[str] = []
    repo_root = Path(__file__).resolve().parent.parent

    blocked = run_shell({"command": "git push origin main", "repo_root": str(repo_root)})
    if blocked.get("ok"):
        errors.append("expected blocked git push")

    allowed = run_shell(
        {
            "command": "echo shell_tool_ok",
            "repo_root": str(repo_root),
            "allowed_commands": ["echo"],
        }
    )
    if not allowed.get("ok") or "shell_tool_ok" not in allowed.get("stdout", ""):
        errors.append("expected echo to succeed")

    if errors:
        emit_json({"ok": False, "errors": errors})
        return 1
    emit_json({"ok": True, "message": "shell_tool self-check passed"})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--command", help="Shell command to run")
    parser.add_argument("--repo-root")
    parser.add_argument("--cwd")
    parser.add_argument("--allowed-commands", nargs="*", default=[])
    parser.add_argument("--blocked-commands", nargs="*", default=[])
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--json-in")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    if args.json_in is not None or not sys.stdin.isatty():
        result = run_shell(load_json_input(args.json_in))
        emit_json(result)
        return 0 if result.get("ok") else 1

    if not args.command:
        parser.error("--command is required unless --json-in or --self-check")

    payload = {
        "command": args.command,
        "repo_root": args.repo_root,
        "cwd": args.cwd,
        "timeout": args.timeout,
    }
    if args.allowed_commands:
        payload["allowed_commands"] = args.allowed_commands
    if args.blocked_commands:
        payload["blocked_commands"] = args.blocked_commands
    result = run_shell(payload)
    emit_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
