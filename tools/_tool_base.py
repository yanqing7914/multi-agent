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
    # "**/<mid>/**" must be handled before the "/**" suffix branch, else a
    # pattern like "**/secrets/**" is read as the literal prefix "**/secrets"
    # and never matches, silently disabling blocked/secret path protection.
    if pattern.startswith("**/") and pattern.endswith("/**"):
        mid = pattern[3:-3]
        if not mid:
            return True
        for segment in path.split("/"):
            if fnmatch.fnmatch(segment, mid):
                return True
        return fnmatch.fnmatch(path.split("/")[-1], mid)
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
    # Also compare against a home-expanded absolute form so that "~/..." patterns
    # (e.g. ~/.ssh/**, ~/.codex/auth.json) are actually enforced instead of skipped.
    abs_path = normalize_path(str(Path(path).expanduser()))
    for pattern in patterns:
        pattern = normalize_path(pattern)
        if pattern.startswith("~/"):
            # Match the home-anchored absolute pattern, and also the bare
            # remainder (e.g. ".ssh/id_rsa") so relative inputs are caught too.
            expanded = normalize_path(str(Path(pattern).expanduser()))
            remainder = pattern[2:]
            if (
                _segment_glob_match(abs_path, expanded)
                or _segment_glob_match(path, expanded)
                or _segment_glob_match(path, remainder)
            ):
                return True
            continue
        if _segment_glob_match(path, pattern) or _segment_glob_match(abs_path, pattern):
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


_SHELL_SEPARATORS = ("&&", "||", "|", ";", "\n")


def _split_subcommands(command: str) -> list[str]:
    """Split a command line into sub-commands on shell separators.

    This is intentionally conservative: it does not fully parse quoting, but it
    prevents "allowed prefix + chained dangerous command" from slipping past the
    allow/deny checks (e.g. "echo hi && rm -rf /").
    """
    parts = [command]
    for sep in _SHELL_SEPARATORS:
        parts = [seg for chunk in parts for seg in chunk.split(sep)]
    return [" ".join(p.strip().lower().split()) for p in parts if p.strip()]


def _is_ordered_subsequence(needles: list[str], haystack: list[str]) -> bool:
    """True if every token in needles appears in haystack in order (gaps allowed)."""
    it = iter(haystack)
    return all(n in it for n in needles)


def _blocked_phrase_matches(tokens: list[str], phrase: list[str]) -> bool:
    """Match a blocked command phrase against a sub-command's tokens.

    - Single keyword (e.g. "deploy") matches only as a whole token.
    - Multi-word phrase (e.g. "git push") matches when its first word appears as
      a token and the remaining words follow in order, tolerating interleaved
      global flags like "git -C /repo push" or "git reset --hard HEAD".
    """
    if not phrase:
        return False
    if len(phrase) == 1:
        return phrase[0] in tokens
    for i, tok in enumerate(tokens):
        if tok == phrase[0] and _is_ordered_subsequence(phrase[1:], tokens[i + 1 :]):
            return True
    return False


def command_is_blocked(command: str, blocked_commands: list[str] | None = None) -> bool:
    blocked = blocked_commands or DEFAULT_BLOCKED_COMMANDS
    # Check every sub-command so chaining/flags (e.g. "git -C /repo push") cannot
    # hide a blocked command behind an allowed-looking prefix.
    for sub in _split_subcommands(command):
        tokens = sub.split()
        for item in blocked:
            if _blocked_phrase_matches(tokens, item.lower().split()):
                return True
    return False


def command_is_allowed(command: str, allowed_commands: list[str] | None = None) -> bool:
    if not allowed_commands:
        return True
    allowed = [a.lower().split() for a in allowed_commands if a.split()]
    subs = _split_subcommands(command)
    if not subs:
        return False
    # Every sub-command must START with an allowed command; a single disallowed
    # segment (e.g. the "rm -rf ..." in "echo hi && rm -rf /") fails the whole
    # command. Anchoring at the start prevents "rm echo" from looking allowed.
    for sub in subs:
        tokens = sub.split()
        if not any(tokens[: len(phrase)] == phrase for phrase in allowed):
            return False
    return True


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
