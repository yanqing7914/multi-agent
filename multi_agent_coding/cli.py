#!/usr/bin/env python3
"""`multi-agent-coding` console entrypoint.

Thin forwarder: every subcommand maps onto one of the bundled mission-control
scripts and is executed with the current interpreter, so behavior is identical
to running the scripts from a repo checkout. Works both from an installed
wheel (scripts bundled under `multi_agent_coding/_bundle/`) and from a source
checkout (scripts at the repo root).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent

# Relative to the bundle/repo root.
COMMANDS: dict[str, dict[str, str]] = {
    "doctor": {
        "script": "scripts/doctor.py",
        "help": "Readiness report per client (skill install, native agents, CLI tooling)",
    },
    "install": {
        "script": "scripts/install_native_skills.py",
        "help": "Install the native skill into client skill directories",
    },
    "cards": {
        "script": "adapters/openclaw/scripts/create_task_cards.py",
        "help": "Generate task cards, ownership, status, run plan (and worktree plan)",
    },
    "status": {
        "script": "adapters/openclaw/scripts/update_task_status.py",
        "help": "Update task status, sync gates, summarize a run",
    },
    "capture": {
        "script": "adapters/openclaw/scripts/capture_changed_files.py",
        "help": "Capture staged+unstaged+untracked changed files for scope audit",
    },
    "audit": {
        "script": "adapters/openclaw/scripts/audit_worker_output.py",
        "help": "Audit Worker output against ownership rules",
    },
    "worktree": {
        "script": "tools/worktree_tool.py",
        "help": "Create/list/remove/plan per-Worker git worktrees",
    },
    "run": {
        "script": "scripts/run_multi_agent.py",
        "help": "Scripted multi-agent run via a client CLI bridge",
    },
}


def bundle_root() -> Path:
    """Root of the skill tree: installed bundle first, then source checkout."""
    installed = PACKAGE_DIR / "_bundle"
    if (installed / "SKILL.md").is_file():
        return installed
    repo = PACKAGE_DIR.parent
    if (repo / "SKILL.md").is_file():
        return repo
    raise FileNotFoundError(
        "multi-agent-coding bundle not found (neither installed _bundle nor repo checkout)"
    )


def forward(script_rel: str, argv: list[str]) -> int:
    script = bundle_root() / script_rel
    if not script.is_file():
        print(json.dumps({"ok": False, "error": f"bundled script missing: {script}"}, indent=2))
        return 1
    proc = subprocess.run([sys.executable, str(script), *argv], check=False)
    return proc.returncode


def print_usage() -> None:
    lines = [
        "usage: multi-agent-coding <command> [args...]",
        "",
        "commands:",
    ]
    width = max(len(name) for name in COMMANDS) + 2
    for name, spec in COMMANDS.items():
        lines.append(f"  {name.ljust(width)}{spec['help']}")
    lines += [
        f"  {'path'.ljust(width)}Print the bundled skill-tree root (SKILL.md lives there)",
        f"  {'self-check'.ljust(width)}Validate the CLI mapping and bundle integrity",
        "",
        "Every command forwards its remaining args to the underlying script",
        "(each supports --help and --self-check).",
    ]
    print("\n".join(lines))


def run_self_check() -> int:
    errors: list[str] = []
    try:
        root = bundle_root()
    except FileNotFoundError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 1
    for name, spec in COMMANDS.items():
        if not (root / spec["script"]).is_file():
            errors.append(f"command '{name}' points at missing script: {spec['script']}")
    for required in ("SKILL.md", "adapters/openclaw/scripts", "tools/worktree_tool.py"):
        if not (root / required).exists():
            errors.append(f"bundle missing {required}")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(
        json.dumps(
            {"ok": True, "message": "multi-agent-coding CLI self-check passed", "bundle_root": str(root)},
            indent=2,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print_usage()
        return 0
    command = args[0]
    if command in {"self-check", "--self-check"}:
        return run_self_check()
    if command == "path":
        print(bundle_root())
        return 0
    spec = COMMANDS.get(command)
    if spec is None:
        print(f"unknown command: {command}\n")
        print_usage()
        return 2
    return forward(spec["script"], args[1:])


if __name__ == "__main__":
    raise SystemExit(main())
