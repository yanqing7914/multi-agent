#!/usr/bin/env python3
"""Cross-adapter dispatcher for multi-agent worker launch (dependency-free)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

RUNTIMES = {
    "openclaw": REPO_ROOT / "adapters" / "openclaw" / "README.md",
    "cursor": REPO_ROOT / "adapters" / "cursor" / "scripts" / "launch_cursor_worker.sh",
    "codex": REPO_ROOT / "adapters" / "codex" / "scripts" / "launch_codex_worker.sh",
    "claude-code": REPO_ROOT / "adapters" / "claude-code" / "scripts" / "launch_claude_worker.sh",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime",
        required=True,
        choices=sorted(RUNTIMES.keys()),
        help="Target client adapter",
    )
    parser.add_argument("--task-card", required=True, help="Path to .codex-multi-agent/tasks/*.md")
    parser.add_argument("--state-dir", help="Mission-control directory")
    parser.add_argument(
        "--mode",
        choices=("local", "acp"),
        default="local",
        help="Claude Code only: local CLI vs ACP handoff",
    )
    parser.add_argument("--foreground", action="store_true", help="Cursor only: run without tmux")
    args = parser.parse_args()

    task_card = Path(args.task_card).expanduser().resolve()
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

    launcher = RUNTIMES[args.runtime]
    cmd = [str(launcher), "--task-card", str(task_card)]
    if args.state_dir:
        cmd.extend(["--state-dir", str(Path(args.state_dir).expanduser().resolve())])
    if args.runtime == "claude-code":
        cmd.extend(["--mode", args.mode])
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
