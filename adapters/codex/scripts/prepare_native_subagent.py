#!/usr/bin/env python3
"""Prepare a Codex native subagent spawn prompt from a task card."""

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
    return safe or "subagent"


def codex_agent_type(role: str) -> str:
    """Map a task-card role to the Codex `spawn_agent` agent_type.

    Codex selects custom agents by their TOML `name` field; we bundle
    `multi-agent-worker` (workspace-write) and `multi-agent-reviewer`
    (sandbox_mode=read-only). Returning those names preserves each agent's
    sandbox + instructions. Roles without a bundled custom agent (Explorer /
    Verifier) fall back to the built-in read-only `explorer`. Reliable custom
    agent_type selection needs Codex CLI >= 0.139.0; older versions ignore it
    and the prompt's role/permission text still enforces the boundary.
    """
    normalized = role.strip().lower()
    if normalized == "worker":
        return "multi-agent-worker"
    if normalized == "reviewer":
        return "multi-agent-reviewer"
    return "explorer"


def native_prompt(task_card_path: Path, card: dict, workspace_root: Path) -> str:
    base = build_worker_prompt(task_card_path, card, workspace_root)
    role = card.get("role") or "subagent"
    skills = [item for item in card.get("may_use_skills", []) if item]
    skill_line = ", ".join(skills) if skills else "none"
    write_permission = card.get("write_permission") or "false"
    return (
        "You are a Codex native subagent spawned by a Main Codex Desktop session.\n"
        "You are not alone in the codebase: other agents may be working on disjoint scopes. "
        "Do not revert or overwrite changes you did not make.\n\n"
        "NATIVE SUBAGENT RULES:\n"
        "1. Follow the task card exactly; do not broaden scope.\n"
        "2. Treat allowed_paths as the hard write/read scope for this task.\n"
        "3. Reviewers, Explorers, and Verifiers are read-only unless the task card says otherwise.\n"
        "4. Workers may edit only allowed_paths and must avoid blocked commands.\n"
        "5. Do not spawn child agents unless may_spawn_sessions is true in the task card.\n"
        "6. Write the JSON and Markdown result reports before claiming completion.\n"
        "7. Return a concise final summary with changed files, validation, blockers, and result report paths.\n\n"
        f"ROLE: {role}\n"
        f"WRITE PERMISSION: {write_permission}\n"
        f"AUTHORIZED SKILLS: {skill_line}\n\n"
        "SKILL USE RULES:\n"
        "- Use only skills listed in AUTHORIZED SKILLS or explicitly attached by Main.\n"
        "- If a named skill is unavailable in this subagent, report blocked instead of substituting a different skill.\n"
        "- A review skill such as ssrd stays read-only and must not expand file, shell, network, or git permissions.\n\n"
        f"{base}"
    )


def write_index(out_dir: Path, records: list[dict]) -> Path:
    index = out_dir / "README.md"
    lines = [
        "# Codex Native Subagent Prompts",
        "",
        "Use these prompts with Codex Desktop's native subagent spawn tools when available.",
        "If native spawning is unavailable, fall back to `prepare_desktop_worker.py` handoff prompts.",
        "",
        "| Task | Role | Agent type | Prompt | Result JSON | Result Markdown |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in records:
        lines.append(
            f"| `{item['task_id']}` | {item['role']} | `{item['agent_type']}` | "
            f"`{Path(item['prompt_path']).name}` | `{item['result_json']}` | `{item['result_markdown']}` |"
        )
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index


def prepare(
    task_card_path: Path,
    state_dir: Path | None,
    out_dir: Path | None,
    skip_preflight: bool,
    include_prompt: bool,
) -> dict:
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

    native_dir = (out_dir or state / "native-subagents").resolve()
    native_dir.mkdir(parents=True, exist_ok=True)
    task_id = card.get("task_id") or task_card_path.stem.split("-")[0]
    session_name = card.get("session_name") or task_card_path.stem
    role = card.get("role") or ""
    agent_type = codex_agent_type(role)
    prompt = native_prompt(task_card_path, card, workspace_root)
    prompt_path = native_dir / f"{safe_name(task_id)}-{safe_name(session_name)}.spawn.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    record = {
        "task_id": task_id,
        "session_name": session_name,
        "role": role,
        "agent_type": agent_type,
        "workspace_root": str(workspace_root),
        "task_card": str(task_card_path),
        "prompt_path": str(prompt_path),
        "result_json": str(card.get("result_json_path") or ""),
        "result_markdown": str(card.get("result_markdown_path") or ""),
        "may_use_skills": card.get("may_use_skills", []),
    }
    index_path = write_index(native_dir, [record])
    payload = {
        "ok": True,
        "runtime": "codex-desktop",
        "mode": "native-subagent",
        "native_dir": str(native_dir),
        "index": str(index_path),
        "preflight": preflight_payload,
        **record,
        "spawn_instruction": {
            "agent_type": agent_type,
            "message_source": str(prompt_path),
            "fork_context": False,
        },
        "instructions": [
            "If Codex Desktop exposes native subagent tools, spawn a subagent with agent_type and the prompt file contents.",
            "Attach or name only the skills listed in may_use_skills; do not let the subagent use unrelated skills.",
            "Wait for the subagent result, then run update_task_status.py --sync and audit_worker_output.py.",
            "If native subagent tools are unavailable, use --runtime codex-desktop handoff mode instead.",
        ],
    }
    if include_prompt:
        payload["prompt"] = prompt
    return payload


def run_self_check() -> int:
    with tempfile.TemporaryDirectory(prefix="codex-native-subagent-") as tmp:
        tmp_path = Path(tmp)
        state_dir = tmp_path / ".codex-multi-agent"
        proc = subprocess.run(
            [
                sys.executable,
                str(CREATE_TASK_CARDS),
                "--task",
                "Native subagent self-check",
                "--mode",
                "review",
                "--modules",
                "docs",
                "--runtime",
                "codex",
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
            print(json.dumps({"ok": False, "error": "no reviewer task cards generated"}, indent=2))
            return 1
        payload = prepare(cards[0], state_dir, tmp_path / "native", skip_preflight=False, include_prompt=False)
        prompt = Path(payload.get("prompt_path", ""))
        if not payload.get("ok") or not prompt.is_file():
            print(json.dumps({"ok": False, "stage": "prepare", "payload": payload}, indent=2))
            return 1
        text = prompt.read_text(encoding="utf-8")
        required = [
            "Codex native subagent",
            "NATIVE SUBAGENT RULES",
            "AUTHORIZED SKILLS: ssrd",
            "JSON:",
            "Markdown:",
            "--- TASK CARD ---",
        ]
        missing = [item for item in required if item not in text]
        if missing:
            print(json.dumps({"ok": False, "missing": missing}, indent=2))
            return 1
        if payload.get("agent_type") != "multi-agent-reviewer":
            print(json.dumps({"ok": False, "error": "reviewer should map to bundled read-only multi-agent-reviewer agent type"}, indent=2))
            return 1
        print(json.dumps({"ok": True, "adapter": "codex-native-subagent", "prompt": str(prompt)}, indent=2))
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-card", help="Path to .codex-multi-agent/tasks/*.md")
    parser.add_argument("--state-dir", help="Mission-control dir (default: parent of tasks/)")
    parser.add_argument("--out", help="Native prompt output dir (default: .codex-multi-agent/native-subagents)")
    parser.add_argument("--skip-preflight", action="store_true", help="Write prompt even if preflight cannot run")
    parser.add_argument("--include-prompt", action="store_true", help="Include full prompt in JSON output")
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
        args.include_prompt,
    )
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
