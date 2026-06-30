#!/usr/bin/env python3
"""Cross-adapter dispatcher for multi-agent worker launch (dependency-free)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

RUNTIMES = {
    "openclaw": REPO_ROOT / "adapters" / "openclaw" / "README.md",
    "hermes": REPO_ROOT / "adapters" / "hermes" / "README.md",
    "cursor-desktop": REPO_ROOT / "adapters" / "cursor" / "scripts" / "prepare_cursor_desktop.py",
    "cursor": REPO_ROOT / "adapters" / "cursor" / "scripts" / "launch_cursor_worker.sh",
    "codex": REPO_ROOT / "adapters" / "codex" / "scripts" / "launch_codex_worker.py",
    "codex-native": REPO_ROOT / "adapters" / "codex" / "scripts" / "prepare_native_subagent.py",
    "codex-native-plan": REPO_ROOT / "adapters" / "codex" / "scripts" / "prepare_native_plan.py",
    "codex-desktop": REPO_ROOT / "adapters" / "codex" / "scripts" / "prepare_desktop_worker.py",
    "claude-desktop": REPO_ROOT / "adapters" / "claude-code" / "scripts" / "prepare_claude_desktop.py",
    "claude-code": REPO_ROOT / "adapters" / "claude-code" / "scripts" / "launch_claude_worker.sh",
}


def launcher_cmd(launcher: Path, args: list[str]) -> list[str]:
    if launcher.suffix == ".sh":
        return ["bash", str(launcher), *args]
    if launcher.suffix == ".py":
        return [sys.executable, str(launcher), *args]
    return [str(launcher), *args]


def self_check() -> int:
    missing = [name for name, path in RUNTIMES.items() if path.suffix in {".py", ".sh"} and not path.is_file()]
    if missing:
        print(json.dumps({"ok": False, "missing_runtimes": missing}, indent=2))
        return 1
    with tempfile.TemporaryDirectory(prefix="run-multi-agent-") as tmp:
        state_dir = Path(tmp) / ".codex-multi-agent"
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "adapters" / "openclaw" / "scripts" / "create_task_cards.py"),
                "--task",
                "Dispatcher self-check",
                "--mode",
                "review",
                "--modules",
                "docs",
                "--runtime",
                "codex",
                "--workspace-root",
                str(REPO_ROOT),
                "--out",
                str(state_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(json.dumps({"ok": False, "stage": "create_task_cards", "output": proc.stderr or proc.stdout}, indent=2))
            return 1
        proc = subprocess.run(
            [sys.executable, __file__, "--runtime", "codex-native-plan", "--state-dir", str(state_dir)],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(json.dumps({"ok": False, "stage": "codex-native-plan", "output": proc.stderr or proc.stdout}, indent=2))
            return 1
        payload = json.loads(proc.stdout)
        if not payload.get("ok") or not payload.get("records"):
            print(json.dumps({"ok": False, "stage": "parse_plan", "payload": payload}, indent=2))
            return 1
    print(json.dumps({"ok": True, "runtimes": sorted(RUNTIMES)}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime",
        choices=sorted(RUNTIMES.keys()),
        help="Target client adapter",
    )
    parser.add_argument("--task-card", help="Path to .codex-multi-agent/tasks/*.md")
    parser.add_argument("--state-dir", help="Mission-control directory")
    parser.add_argument(
        "--mode",
        choices=("local", "acp"),
        default="local",
        help="Claude Code only: local CLI vs ACP handoff",
    )
    parser.add_argument("--foreground", action="store_true", help="Cursor only: run without tmux")
    parser.add_argument("--self-check", action="store_true", help="Run dispatcher validation")
    args = parser.parse_args()

    if args.self_check:
        return self_check()

    if not args.runtime:
        parser.error("--runtime is required unless --self-check is used")

    task_card = Path(args.task_card).expanduser().resolve() if args.task_card else None
    if args.runtime != "codex-native-plan":
        if task_card is None:
            print(json.dumps({"ok": False, "error": "--task-card is required for this runtime"}))
            return 1
        if not task_card.is_file():
            print(json.dumps({"ok": False, "error": f"task card not found: {task_card}"}))
            return 1

    if args.runtime == "openclaw":
        print(
            json.dumps(
                {
                    "ok": True,
                    "runtime": "openclaw",
                    "message": "OpenClaw uses sessions_spawn/sessions_send — see adapters/openclaw/QUICKSTART.md",
                    "task_card": str(task_card),
                    "handoff": "Paste task card into sessions_send; use openclaw_handoff block in card",
                },
                indent=2,
            )
        )
        return 0

    if args.runtime == "hermes":
        print(
            json.dumps(
                {
                    "ok": True,
                    "runtime": "hermes",
                    "message": "Hermes uses its native MCP client + mission-control scripts — see adapters/hermes/QUICKSTART.md",
                    "task_card": str(task_card),
                    "handoff": "Register the MCP coordinator (scripts/configure_mcp.py --client hermes), then drive Workers via Hermes MCP tools and the OpenClaw mission-control scripts.",
                },
                indent=2,
            )
        )
        return 0

    launcher = RUNTIMES[args.runtime]
    launcher_args = [] if args.runtime == "codex-native-plan" else ["--task-card", str(task_card)]
    if args.state_dir:
        launcher_args.extend(["--state-dir", str(Path(args.state_dir).expanduser().resolve())])
    if args.runtime == "claude-code":
        launcher_args.extend(["--mode", args.mode])
    cmd = launcher_cmd(launcher, launcher_args)
    if args.runtime == "cursor" and args.foreground:
        cmd = [
            sys.executable,
            str(launcher.parent / "launch_cursor_worker.py"),
            "--task-card",
            str(task_card),
            "--foreground",
        ]
        if args.state_dir:
            cmd.extend(["--state-dir", str(Path(args.state_dir).expanduser().resolve())])

    proc = subprocess.run(cmd, check=False)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
