#!/usr/bin/env python3
"""Dependency-free git status/diff helper for Workers and Verifiers."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from _tool_base import (
    DEFAULT_BLOCKED_PATHS,
    emit_json,
    load_json_input,
    normalize_path,
    path_matches,
    resolve_repo_root,
    tool_result,
    validate_path_scope,
)


def run_git(args: list[str], repo_root: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def git_status(repo_root: Path) -> dict:
    code, stdout, stderr = run_git(["status", "--porcelain"], repo_root)
    if code != 0:
        return tool_result(False, action="status", error=stderr.strip() or stdout.strip(), returncode=code)
    entries = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append({"status": status, "path": normalize_path(path)})
    return tool_result(True, action="status", entries=entries, count=len(entries), returncode=code)


def git_diff(repo_root: Path, paths: list[str] | None = None) -> dict:
    cmd = ["diff"]
    if paths:
        cmd.extend(paths)
    code, stdout, stderr = run_git(cmd, repo_root)
    if code not in (0, 1):
        return tool_result(False, action="diff", error=stderr.strip() or stdout.strip(), returncode=code)
    return tool_result(True, action="diff", diff=stdout, returncode=code, changed=bool(stdout.strip()))


def git_name_only(repo_root: Path, paths: list[str] | None = None) -> dict:
    cmd = ["diff", "--name-only"]
    if paths:
        cmd.extend(paths)
    code, stdout, stderr = run_git(cmd, repo_root)
    if code not in (0, 1):
        return tool_result(False, action="name-only", error=stderr.strip() or stdout.strip(), returncode=code)
    files = [normalize_path(line) for line in stdout.splitlines() if line.strip()]
    if paths:
        scoped = [item for item in files if path_matches(item, paths)]
        files = scoped
    return tool_result(True, action="name-only", files=files, count=len(files), returncode=code)


def invoke(payload: dict) -> dict:
    action = payload.get("action", "status")
    repo_root = resolve_repo_root(payload.get("repo_root"))
    allowed_paths = payload.get("allowed_paths")
    blocked_paths = payload.get("blocked_paths") or DEFAULT_BLOCKED_PATHS
    paths = payload.get("paths") or []

    for path in paths:
        ok, reason = validate_path_scope(path, repo_root, allowed_paths, blocked_paths)
        if not ok:
            return tool_result(False, action=action, error=f"path scope rejected: {path}: {reason}")

    if action == "status":
        return git_status(repo_root)
    if action == "diff":
        return git_diff(repo_root, paths or None)
    if action == "name-only":
        return git_name_only(repo_root, allowed_paths or paths or None)
    return tool_result(False, error=f"unknown action: {action}")


def run_self_check() -> int:
    errors: list[str] = []
    repo_root = Path(__file__).resolve().parent.parent
    repo_check, _, _ = run_git(["rev-parse", "--is-inside-work-tree"], repo_root)
    temp_dir: tempfile.TemporaryDirectory | None = None
    if repo_check != 0:
        temp_dir = tempfile.TemporaryDirectory(prefix="git-tool-selfcheck-")
        repo_root = Path(temp_dir.name)
        init_code, _, init_stderr = run_git(["init"], repo_root)
        if init_code != 0:
            emit_json({"ok": False, "errors": [f"git init failed: {init_stderr.strip()}"]})
            temp_dir.cleanup()
            return 1
    status = git_status(repo_root)
    if not status.get("ok"):
        errors.append(f"git status failed: {status.get('error')}")
    diff = git_diff(repo_root)
    if not diff.get("ok"):
        errors.append(f"git diff failed: {diff.get('error')}")
    names = git_name_only(repo_root, ["tools/**"])
    if not names.get("ok"):
        errors.append(f"git name-only failed: {names.get('error')}")

    payload = invoke({"action": "status", "repo_root": str(repo_root)})
    if not payload.get("ok"):
        errors.append("invoke(status) failed")

    if errors:
        emit_json({"ok": False, "errors": errors})
        if temp_dir:
            temp_dir.cleanup()
        return 1
    emit_json({"ok": True, "message": "git_tool self-check passed"})
    if temp_dir:
        temp_dir.cleanup()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("status", "diff", "name-only"), default="status")
    parser.add_argument("--repo-root", help="Repository root (default: cwd)")
    parser.add_argument("--paths", nargs="*", default=[], help="Optional path filters")
    parser.add_argument("--allowed-paths", nargs="*", default=[], help="Scope filter for name-only")
    parser.add_argument("--json-in", help="JSON input string (otherwise stdin or flags)")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    if args.json_in is not None or not sys.stdin.isatty():
        payload = load_json_input(args.json_in)
        result = invoke(payload)
        emit_json(result)
        return 0 if result.get("ok") else 1

    payload = {
        "action": args.action,
        "repo_root": args.repo_root,
        "paths": args.paths,
    }
    if args.allowed_paths:
        payload["allowed_paths"] = args.allowed_paths
    result = invoke(payload)
    emit_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
