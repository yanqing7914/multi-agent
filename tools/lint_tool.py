#!/usr/bin/env python3
"""Detect and run common linters (dependency-free, best-effort)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from shutil import which

from _tool_base import (
    command_is_allowed,
    command_is_blocked,
    emit_json,
    load_json_input,
    resolve_repo_root,
    tool_result,
)

LINTER_CATALOG: list[dict] = [
    {"linter": "ruff", "command": "ruff check .", "kind": "python", "bin": "ruff"},
    {"linter": "flake8", "command": "flake8 .", "kind": "python", "bin": "flake8"},
    {"linter": "mypy", "command": "mypy .", "kind": "python", "bin": "mypy"},
    {"linter": "pyright", "command": "pyright", "kind": "python", "bin": "pyright"},
    {"linter": "eslint", "command": "eslint .", "kind": "javascript", "bin": "eslint", "needs_package_json": True},
    {"linter": "prettier", "command": "prettier --check .", "kind": "javascript", "bin": "prettier", "needs_package_json": True},
    {"linter": "golangci-lint", "command": "golangci-lint run", "kind": "go", "bin": "golangci-lint", "needs_go_mod": True},
    {"linter": "cargo-clippy", "command": "cargo clippy", "kind": "rust", "bin": "cargo", "needs_cargo_toml": True},
    {"linter": "rustfmt", "command": "cargo fmt --check", "kind": "rust", "bin": "cargo", "needs_cargo_toml": True},
]


def detect(repo_root: Path) -> dict:
    linters: list[dict] = []
    has_package_json = (repo_root / "package.json").exists()
    has_go_mod = (repo_root / "go.mod").exists()
    has_cargo = (repo_root / "Cargo.toml").exists()

    for entry in LINTER_CATALOG:
        if entry.get("needs_package_json") and not has_package_json:
            continue
        if entry.get("needs_go_mod") and not has_go_mod:
            continue
        if entry.get("needs_cargo_toml") and not has_cargo:
            continue
        if entry["linter"] in {"cargo-clippy", "rustfmt"}:
            if not which("cargo"):
                continue
        elif not which(entry["bin"]):
            continue
        linters.append({k: v for k, v in entry.items() if k not in {"bin", "needs_package_json", "needs_go_mod", "needs_cargo_toml"}})

    # Prefer ruff over flake8 when both exist
    names = {item["linter"] for item in linters}
    if "ruff" in names and "flake8" in names:
        linters = [item for item in linters if item["linter"] != "flake8"]

    return tool_result(True, action="detect", linters=linters, count=len(linters))


def run_lint(repo_root: Path, linter: str | None, command: str | None, allowed_commands: list[str] | None, blocked_commands: list[str] | None) -> dict:
    detected = detect(repo_root)
    selected = None
    if command:
        selected = {"linter": linter or "custom", "command": command}
    elif linter:
        for item in detected.get("linters", []):
            if item["linter"] == linter:
                selected = item
                break
    elif detected.get("linters"):
        selected = detected["linters"][0]

    if not selected:
        return tool_result(False, action="run", error="no linter detected; pass --command explicitly")

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
        linter=selected.get("linter"),
        command=cmd_text,
        returncode=proc.returncode,
        stdout=proc.stdout[-8000:],
        stderr=proc.stderr[-8000:],
    )


def invoke(payload: dict) -> dict:
    action = payload.get("action", "detect")
    repo_root = resolve_repo_root(payload.get("repo_root"))
    if action == "detect":
        return detect(repo_root)
    if action == "run":
        return run_lint(
            repo_root,
            payload.get("linter"),
            payload.get("command"),
            payload.get("allowed_commands"),
            payload.get("blocked_commands"),
        )
    return tool_result(False, error=f"unknown action: {action}")


def run_self_check() -> int:
    errors: list[str] = []
    repo_root = Path(__file__).resolve().parent.parent
    detected = detect(repo_root)
    if not detected.get("ok"):
        errors.append("detect failed")
    payload = invoke({"action": "detect", "repo_root": str(repo_root)})
    if not payload.get("ok"):
        errors.append("invoke detect failed")

    catalog_names = {entry["linter"] for entry in LINTER_CATALOG}
    expected = {"ruff", "flake8", "mypy", "pyright", "eslint", "prettier", "golangci-lint", "cargo-clippy", "rustfmt"}
    if not expected.issubset(catalog_names):
        errors.append("lint catalog missing expected linters")

    if errors:
        emit_json({"ok": False, "errors": errors})
        return 1
    emit_json({"ok": True, "message": "lint_tool self-check passed", "linters": detected.get("linters", []), "catalog": sorted(catalog_names)})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("detect", "run"), default="detect")
    parser.add_argument("--repo-root")
    parser.add_argument("--linter", help="ruff | flake8 | eslint | mypy | pyright | golangci-lint | cargo-clippy | rustfmt | prettier")
    parser.add_argument("--command")
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
            "linter": args.linter,
            "command": args.command,
        }
    )
    emit_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
