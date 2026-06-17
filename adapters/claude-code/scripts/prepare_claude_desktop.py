#!/usr/bin/env python3
"""Prepare Claude Desktop / Claude.ai skill prompts from a task card."""

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

CLAUDE_RULES = [
    "Use this prompt inside Claude Desktop, Claude.ai custom skill context, or Claude Code when a CLI worker is not desired.",
    "Treat this as one scoped task card; do not broaden the task or edit outside allowed_paths.",
    "Reviewers and Explorers are read-only; Workers may edit only allowed_paths when operating in a coding environment.",
    "Write or return both JSON and Markdown result reports before claiming completion.",
    "For fully automatic repository edits, prefer Claude Code CLI or OpenClaw ACP mode.",
]


def run_self_check() -> int:
    with tempfile.TemporaryDirectory(prefix="claude-desktop-prompt-") as tmp:
        tmp_path = Path(tmp)
        state_dir = tmp_path / ".codex-multi-agent"
        proc = subprocess.run(
            [
                sys.executable,
                str(CREATE_TASK_CARDS),
                "--task",
                "Claude Desktop prompt self-check",
                "--mode",
                "review",
                "--modules",
                "docs",
                "--runtime",
                "claude-code",
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
            tmp_path / "claude-prompts",
            client_name="Claude Desktop",
            mode_name="desktop-skill-prompt",
            out_subdir="claude-desktop",
            file_suffix="claude",
            extra_rules=CLAUDE_RULES,
        )
        prompt = Path(payload.get("prompt_path", ""))
        text = prompt.read_text(encoding="utf-8") if prompt.is_file() else ""
        required = ["Claude Desktop", "DESKTOP-SKILL-PROMPT RULES", "AUTHORIZED SKILLS: ssrd", "--- TASK CARD ---"]
        missing = [item for item in required if item not in text]
        ok = bool(payload.get("ok")) and not missing
        print(json.dumps({"ok": ok, "adapter": "claude-desktop", "prompt": str(prompt), "missing": missing}, indent=2))
        return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-card", help="Path to .codex-multi-agent/tasks/*.md")
    parser.add_argument("--state-dir", help="Mission-control dir (default: parent of tasks/)")
    parser.add_argument("--out", help="Prompt output dir (default: .codex-multi-agent/claude-desktop)")
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
        client_name="Claude Desktop",
        mode_name="desktop-skill-prompt",
        out_subdir="claude-desktop",
        file_suffix="claude",
        skip_preflight=args.skip_preflight,
        include_prompt=args.include_prompt,
        extra_rules=CLAUDE_RULES,
        instructions=[
            "Use the generated prompt inside Claude Desktop / Claude.ai custom skill context when repository tooling is available.",
            "For automatic local edits, use `--runtime claude-code` with Claude Code CLI.",
            "For OpenClaw/Her production orchestration, use `--runtime claude-code --mode acp`.",
            "After result reports exist, run gate sync and scope audit.",
        ],
    )
    return print_payload(payload)


if __name__ == "__main__":
    raise SystemExit(main())
