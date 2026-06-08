#!/usr/bin/env python3
"""Prepare a Codex Desktop worker handoff prompt from a task card."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent.parent / "_shared"
sys.path.insert(0, str(SHARED))

from bridge import build_worker_prompt, parse_task_card, run_preflight, workspace_root_from_card  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CREATE_TASK_CARDS = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "create_task_cards.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-")
    return safe or "worker"


def desktop_prompt(task_card_path: Path, card: dict, workspace_root: Path) -> str:
    base = build_worker_prompt(task_card_path, card, workspace_root)
    result_json = card.get("result_json_path") or ""
    result_markdown = card.get("result_markdown_path") or ""
    return (
        "You are a Codex Desktop Worker assigned by a Main Codex Desktop session.\n"
        "Treat this as a scoped subtask. Do not broaden the task, do not edit outside allowed_paths, "
        "and do not ask the user for unrelated context.\n\n"
        "DESKTOP HANDOFF RULES:\n"
        "1. Work in the exact workspace_root below.\n"
        "2. Run the mandatory preflight before reading or editing files.\n"
        "3. Write the JSON result report and Markdown result report to the exact paths below.\n"
        "4. When done, reply with the completion_signal from the task card and a short summary.\n"
        "5. If you cannot write the result files, return status=blocked and explain why.\n\n"
        f"RESULT JSON: {result_json}\n"
        f"RESULT MARKDOWN: {result_markdown}\n\n"
        f"{base}"
    )


def write_index(out_dir: Path, records: list[dict]) -> Path:
    index = out_dir / "README.md"
    lines = [
        "# Codex Desktop Worker Handoffs",
        "",
        "Open each prompt in a separate Codex Desktop session or task. Each Worker must write the result reports listed in its prompt.",
        "",
        "| Task | Role | Prompt | Result JSON | Result Markdown |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in records:
        lines.append(
            f"| `{item['task_id']}` | {item['role']} | `{Path(item['prompt_path']).name}` | "
            f"`{item['result_json']}` | `{item['result_markdown']}` |"
        )
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index


def prepare(task_card_path: Path, state_dir: Path | None, out_dir: Path | None, skip_preflight: bool) -> dict:
    if not task_card_path.is_file():
        return {"ok": False, "error": f"task card not found: {task_card_path}"}

    state = state_dir.resolve() if state_dir else task_card_path.parent.parent
    card = parse_task_card(task_card_path)
    workspace_root = workspace_root_from_card(card, state)
    required_paths = [str(path) for path in card.get("required_paths", [])]

    preflight_payload: dict = {"skipped": True}
    if not skip_preflight:
        code, preflight_payload = run_preflight(workspace_root, required_paths)
        if code != 0:
            return {"ok": False, "stage": "preflight", **preflight_payload}

    handoff_dir = (out_dir or state / "desktop-workers").resolve()
    handoff_dir.mkdir(parents=True, exist_ok=True)
    task_id = card.get("task_id") or task_card_path.stem.split("-")[0]
    session_name = card.get("session_name") or task_card_path.stem
    prompt_path = handoff_dir / f"{safe_name(task_id)}-{safe_name(session_name)}.prompt.md"
    prompt_path.write_text(desktop_prompt(task_card_path, card, workspace_root), encoding="utf-8")

    record = {
        "task_id": task_id,
        "session_name": session_name,
        "role": card.get("role", ""),
        "workspace_root": str(workspace_root),
        "task_card": str(task_card_path),
        "prompt_path": str(prompt_path),
        "result_json": str(card.get("result_json_path") or ""),
        "result_markdown": str(card.get("result_markdown_path") or ""),
    }
    index_path = write_index(handoff_dir, [record])
    return {
        "ok": True,
        "runtime": "codex-desktop",
        "mode": "desktop-handoff",
        "handoff_dir": str(handoff_dir),
        "index": str(index_path),
        "preflight": preflight_payload,
        **record,
        "instructions": [
            "Open prompt_path in a new Codex Desktop session or task.",
            "Require the Worker to write both result reports before claiming completion.",
            "After the Worker finishes, run update_task_status.py --sync and audit_worker_output.py.",
        ],
    }


def run_self_check() -> int:
    with tempfile.TemporaryDirectory(prefix="codex-desktop-handoff-") as tmp:
        tmp_path = Path(tmp)
        state_dir = tmp_path / ".codex-multi-agent"
        proc = subprocess.run(
            [
                sys.executable,
                str(CREATE_TASK_CARDS),
                "--task",
                "Desktop handoff self-check",
                "--mode",
                "implement",
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
        cards = sorted((state_dir / "tasks").glob("*.md"))
        if not cards:
            print(json.dumps({"ok": False, "error": "no task cards generated"}, indent=2))
            return 1
        payload = prepare(cards[0], state_dir, tmp_path / "handoffs", skip_preflight=False)
        prompt = Path(payload.get("prompt_path", ""))
        if not payload.get("ok") or not prompt.is_file():
            print(json.dumps({"ok": False, "stage": "prepare", "payload": payload}, indent=2))
            return 1
        text = prompt.read_text(encoding="utf-8")
        required = ["Codex Desktop Worker", "DESKTOP HANDOFF RULES", "RESULT JSON", "--- TASK CARD ---"]
        missing = [item for item in required if item not in text]
        if missing:
            print(json.dumps({"ok": False, "missing": missing}, indent=2))
            return 1
        print(json.dumps({"ok": True, "adapter": "codex-desktop", "prompt": str(prompt)}, indent=2))
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-card", help="Path to .codex-multi-agent/tasks/*.md")
    parser.add_argument("--state-dir", help="Mission-control dir (default: parent of tasks/)")
    parser.add_argument("--out", help="Handoff output dir (default: .codex-multi-agent/desktop-workers)")
    parser.add_argument("--skip-preflight", action="store_true", help="Write handoff even if preflight cannot run")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()
    if not args.task_card:
        parser.error("--task-card is required unless --self-check is used")

    payload = prepare(
        Path(args.task_card).expanduser().resolve(),
        Path(args.state_dir).expanduser().resolve() if args.state_dir else None,
        Path(args.out).expanduser().resolve() if args.out else None,
        args.skip_preflight,
    )
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
