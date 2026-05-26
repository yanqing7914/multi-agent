#!/usr/bin/env python3
"""Shared helpers for dependency-free tool wrappers (stdlib only)."""

from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_BLOCKED_PATHS = [
    ".env",
    ".env.*",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "~/.ssh/**",
    "~/.codex/auth.json",
    "**/*.pem",
    "**/*.key",
]

DEFAULT_BLOCKED_COMMANDS = [
    "npm install",
    "pnpm install",
    "git push",
    "git reset --hard",
    "deploy",
    "publish",
]


def normalize_path(path: str) -> str:
    path = path.replace("\\", "/").strip()
    while path.startswith("./"):
        path = path[2:]
    return path


def _segment_glob_match(path: str, pattern: str) -> bool:
    if pattern == "**":
        return True
    if pattern.endswith("/**"):
        base = pattern[:-3]
        return path == base or path.startswith(base + "/")
    if pattern.startswith("**/"):
        suffix = pattern[3:]
        if fnmatch.fnmatch(path, suffix):
            return True
        for index in range(path.count("/") + 1):
            candidate = "/".join(path.split("/")[index:])
            if fnmatch.fnmatch(candidate, suffix):
                return True
        return False
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path.split("/")[-1], pattern)


def path_matches(path: str, patterns: list[str]) -> bool:
    path = normalize_path(path)
    for pattern in patterns:
        pattern = normalize_path(pattern)
        if pattern.startswith("~/"):
            continue
        if _segment_glob_match(path, pattern):
            return True
    return False


def is_path_in_scope(path: str, repo_root: Path, allowed_paths: list[str] | None = None) -> bool:
    """Return True when path resolves under repo_root and matches allowed_paths (if any)."""
    try:
        resolved = Path(path).expanduser().resolve()
        root = repo_root.expanduser().resolve()
        rel = resolved.relative_to(root)
        rel_str = normalize_path(str(rel))
    except ValueError:
        return False
    if allowed_paths:
        return path_matches(rel_str, allowed_paths)
    return True


def is_path_blocked(path: str, blocked_paths: list[str] | None = None) -> bool:
    blocked = blocked_paths or DEFAULT_BLOCKED_PATHS
    return path_matches(normalize_path(path), blocked)


def validate_path_scope(
    path: str,
    repo_root: Path,
    allowed_paths: list[str] | None = None,
    blocked_paths: list[str] | None = None,
) -> tuple[bool, str]:
    if is_path_blocked(path, blocked_paths):
        return False, "path matches blocked/secret patterns"
    if not is_path_in_scope(path, repo_root, allowed_paths):
        return False, "path outside allowed scope"
    return True, "ok"


def command_is_blocked(command: str, blocked_commands: list[str] | None = None) -> bool:
    blocked = blocked_commands or DEFAULT_BLOCKED_COMMANDS
    normalized = " ".join(command.strip().lower().split())
    for item in blocked:
        if item.lower() in normalized:
            return True
    return False


def command_is_allowed(command: str, allowed_commands: list[str] | None = None) -> bool:
    if not allowed_commands:
        return True
    normalized = " ".join(command.strip().lower().split())
    return any(token.lower() in normalized for token in allowed_commands)


def load_json_input(payload: str | None = None) -> dict:
    if payload:
        data = json.loads(payload)
    else:
        text = sys.stdin.read().strip()
        data = json.loads(text) if text else {}
    if not isinstance(data, dict):
        raise ValueError("JSON input must be an object")
    return data


def emit_json(data: dict, indent: int = 2) -> None:
    print(json.dumps(data, indent=indent))


def tool_result(ok: bool, **fields: Any) -> dict:
    payload = {"ok": ok, **fields}
    return payload


def resolve_repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).expanduser().resolve()
    return Path.cwd().resolve()
