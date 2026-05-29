#!/usr/bin/env python3
"""rg/find-based file listing and simple grep (dependency-free)."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from shutil import which

from _tool_base import (
    DEFAULT_BLOCKED_PATHS,
    emit_json,
    is_path_blocked,
    load_json_input,
    normalize_path,
    path_matches,
    resolve_repo_root,
    tool_result,
)


def _walk_files(repo_root: Path, glob_pattern: str | None = None) -> list[str]:
    files: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", "node_modules", ".pytest_cache"}]
        for name in filenames:
            rel = normalize_path(str(Path(dirpath, name).relative_to(repo_root)))
            if is_path_blocked(rel, DEFAULT_BLOCKED_PATHS):
                continue
            if glob_pattern and not path_matches(rel, [glob_pattern]):
                continue
            files.append(rel)
    return sorted(files)


def _run_rg(args: list[str], repo_root: Path) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["rg", *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None


def list_files(repo_root: Path, glob_pattern: str | None = None, allowed_paths: list[str] | None = None) -> dict:
    if which("rg") and glob_pattern:
        proc = _run_rg(["--files", "-g", glob_pattern], repo_root)
        if proc and proc.returncode in (0, 1):
            files = [normalize_path(line) for line in proc.stdout.splitlines() if line.strip()]
        else:
            files = _walk_files(repo_root, glob_pattern)
    else:
        files = _walk_files(repo_root, glob_pattern)

    if allowed_paths:
        files = [item for item in files if path_matches(item, allowed_paths)]
    files = [item for item in files if not is_path_blocked(item)]
    return tool_result(True, action="list", files=files, count=len(files))


def grep_files(repo_root: Path, pattern: str, glob_pattern: str | None = None, allowed_paths: list[str] | None = None) -> dict:
    if which("rg"):
        cmd = ["rg", "-n", pattern, "."]
        if glob_pattern:
            cmd.extend(["-g", glob_pattern])
        proc = _run_rg(cmd[1:], repo_root)
        if proc and proc.returncode in (0, 1):
            matches = []
            for line in proc.stdout.splitlines():
                if not line.strip():
                    continue
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    rel = normalize_path(parts[0])
                    if allowed_paths and not path_matches(rel, allowed_paths):
                        continue
                    if is_path_blocked(rel):
                        continue
                    matches.append({"file": rel, "line": int(parts[1]), "text": parts[2]})
            return tool_result(True, action="grep", pattern=pattern, matches=matches, count=len(matches))

    regex = re.compile(pattern)
    matches = []
    for rel in list_files(repo_root, glob_pattern, allowed_paths).get("files", []):
        path = repo_root / rel
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for index, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                matches.append({"file": rel, "line": index, "text": line.strip()})
    return tool_result(True, action="grep", pattern=pattern, matches=matches, count=len(matches))


def invoke(payload: dict) -> dict:
    action = payload.get("action", "list")
    repo_root = resolve_repo_root(payload.get("repo_root"))
    glob_pattern = payload.get("glob")
    allowed_paths = payload.get("allowed_paths")
    if action == "list":
        return list_files(repo_root, glob_pattern, allowed_paths)
    if action == "grep":
        pattern = payload.get("pattern")
        if not pattern:
            return tool_result(False, error="pattern is required for grep")
        return grep_files(repo_root, pattern, glob_pattern, allowed_paths)
    return tool_result(False, error=f"unknown action: {action}")


def run_self_check() -> int:
    errors: list[str] = []
    repo_root = Path(__file__).resolve().parent.parent
    listed = list_files(repo_root, "tools/*.py")
    if not listed.get("ok") or listed.get("count", 0) < 1:
        errors.append("list files failed")
    grep = grep_files(repo_root, "def invoke", glob_pattern="tools/*.py")
    if not grep.get("ok") or grep.get("count", 0) < 1:
        errors.append("grep failed")
    if errors:
        emit_json({"ok": False, "errors": errors})
        return 1
    emit_json({"ok": True, "message": "repo_index_tool self-check passed"})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("list", "grep"), default="list")
    parser.add_argument("--repo-root")
    parser.add_argument("--glob", help="Glob filter, e.g. '**/*.py'")
    parser.add_argument("--pattern", help="Regex pattern for grep")
    parser.add_argument("--allowed-paths", nargs="*", default=[])
    parser.add_argument("--json-in")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    if args.json_in is not None or not sys.stdin.isatty():
        result = invoke(load_json_input(args.json_in))
        emit_json(result)
        return 0 if result.get("ok") else 1

    payload = {
        "action": args.action,
        "repo_root": args.repo_root,
        "glob": args.glob,
        "pattern": args.pattern,
    }
    if args.allowed_paths:
        payload["allowed_paths"] = args.allowed_paths
    result = invoke(payload)
    emit_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
