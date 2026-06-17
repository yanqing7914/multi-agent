#!/usr/bin/env python3
"""Prepare Cursor Desktop agent prompts from a task card."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent.parent / "_shared"
sys.path.insert(0, str(SHARED))

from desktop_prompt import prepare_prompt, print_payload  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CREATE_TASK_CARDS = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "create_task_cards.py"

CURSOR_RULES = [
    "Use Cursor Agent in the target workspace, with this package's Cursor rules installed when possible.",
    "Treat this as one scoped task card; do not broaden the task or edit outside allowed_paths.",
    "Reviewers and Explorers are read-only; Workers may edit only allowed_paths.",
    "Write both JSON and Markdown result reports before claiming completion.",
    "If you need automatic background execution, use the Cursor CLI launcher instead.",
]


def run_self_check() -> int:
    with tempfile.TemporaryDirectory(prefix="cursor-desktop-prompt-") as tmp:
        tmp_path = Path(tmp)
        state_dir = tmp_path / ".codex-multi-agent"
        proc = subprocess.run(
            [
                sys.executable,
                str(CREATE_TASK_CARDS),
                "--task",
                "Cursor Desktop prompt self-check",
                "--mode",
                "review",
                "--modules",
                "docs",
                "--runtime",
                "cursor",
                "--review-skill",
                "ssrd",
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
        cards = sorted((state_dir / "tasks").glob("*reviewer*.md"))
        if not cards:
            print(json.dumps({"ok": False, "error": "no reviewer cards generated"}, indent=2))
            return 1
        payload = prepare_prompt(
            cards[0],
            state_dir,
            tmp_path / "cursor-prompts",
            client_name="Cursor Desktop",
            mode_name="desktop-prompt",
            out_subdir="cursor-desktop",
            file_suffix="cursor",
            extra_rules=CURSOR_RULES,
        )
        prompt = Path(payload.get("prompt_path", ""))
        text = prompt.read_text(encoding="utf-8") if prompt.is_file() else ""
        required = ["Cursor Desktop", "DESKTOP-PROMPT RULES", "AUTHORIZED SKILLS: ssrd", "--- TASK CARD ---"]
        missing = [item for item in required if item not in text]
        ok = bool(payload.get("ok")) and not missing
        print(json.dumps({"ok": ok, "adapter": "cursor-desktop", "prompt": str(prompt), "missing": missing}, indent=2))
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-card", help="Path to .codex-multi-agent/tasks/*.md")
    parser.add_argument("--state-dir", help="Mission-control dir (default: parent of tasks/)")
    parser.add_argument("--out", help="Prompt output dir (default: .codex-multi-agent/cursor-desktop)")
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("--include-prompt", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()
    if not args.task_card:
        parser.error("--task-card is required unless --self-check is used")

    payload = prepare_prompt(
        Path(args.task_card).expanduser().resolve(),
        Path(args.state_dir).expanduser().resolve() if args.state_dir else None,
        Path(args.out).expanduser().resolve() if args.out else None,
        client_name="Cursor Desktop",
        mode_name="desktop-prompt",
        out_subdir="cursor-desktop",
        file_suffix="cursor",
        skip_preflight=args.skip_preflight,
        include_prompt=args.include_prompt,
        extra_rules=CURSOR_RULES,
        instructions=[
            "Install or merge `.cursor/rules/multi-agent-coding.mdc` into the target workspace.",
            "Open the generated prompt in Cursor Agent or paste it into a new scoped chat.",
            "Wait for result JSON/Markdown, then run gate sync and scope audit.",
            "For automatic background workers, use `--runtime cursor` with Cursor CLI.",
        ],
    )
    return print_payload(payload)


if __name__ == "__main__":
    raise SystemExit(main())
