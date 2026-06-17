#!/usr/bin/env python3
"""Shared helpers for Desktop-app prompt handoff adapters."""

from __future__ import annotations

import json
from pathlib import Path

from bridge import build_worker_prompt, parse_task_card, run_preflight, workspace_root_from_card


def safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value).strip("-")
    return safe or "agent"


def task_prompt(
    task_card_path: Path,
    card: dict,
    workspace_root: Path,
    *,
    client_name: str,
    mode_name: str,
    extra_rules: list[str] | None = None,
) -> str:
    base = build_worker_prompt(task_card_path, card, workspace_root)
    skills = [item for item in card.get("may_use_skills", []) if item]
    skill_line = ", ".join(skills) if skills else "none"
    rules = "\n".join(f"{idx}. {rule}" for idx, rule in enumerate(extra_rules or [], start=1))
    if rules:
        rules = f"\n{mode_name.upper()} RULES:\n{rules}\n"
    return (
        f"You are a scoped {client_name} agent participating in a multi-agent coding workflow.\n"
        "You are not alone in the codebase: other agents may be working on disjoint scopes. "
        "Do not revert or overwrite changes you did not make.\n"
        f"{rules}\n"
        f"AUTHORIZED SKILLS: {skill_line}\n"
        "Use only authorized skills. If a named skill is unavailable, report status=blocked instead of substituting another method.\n\n"
        f"{base}"
    )


def write_index(out_dir: Path, records: list[dict], title: str, description: str) -> Path:
    index = out_dir / "README.md"
    lines = [
        f"# {title}",
        "",
        description,
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


def prepare_prompt(
    task_card_path: Path,
    state_dir: Path | None,
    out_dir: Path | None,
    *,
    client_name: str,
    mode_name: str,
    out_subdir: str,
    file_suffix: str,
    skip_preflight: bool = False,
    include_prompt: bool = False,
    extra_rules: list[str] | None = None,
    instructions: list[str] | None = None,
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

    prompt_dir = (out_dir or state / out_subdir).resolve()
    prompt_dir.mkdir(parents=True, exist_ok=True)
    task_id = card.get("task_id") or task_card_path.stem.split("-")[0]
    session_name = card.get("session_name") or task_card_path.stem
    prompt = task_prompt(
        task_card_path,
        card,
        workspace_root,
        client_name=client_name,
        mode_name=mode_name,
        extra_rules=extra_rules,
    )
    prompt_path = prompt_dir / f"{safe_name(task_id)}-{safe_name(session_name)}.{file_suffix}.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    record = {
        "task_id": task_id,
        "session_name": session_name,
        "role": card.get("role", ""),
        "workspace_root": str(workspace_root),
        "task_card": str(task_card_path),
        "prompt_path": str(prompt_path),
        "result_json": str(card.get("result_json_path") or ""),
        "result_markdown": str(card.get("result_markdown_path") or ""),
        "may_use_skills": card.get("may_use_skills", []),
    }
    index_path = write_index(
        prompt_dir,
        [record],
        f"{client_name} Desktop Prompts",
        f"Open or paste each prompt into {client_name}. Each agent must write the result reports listed in its prompt.",
    )
    payload = {
        "ok": True,
        "runtime": client_name.lower().replace(" ", "-"),
        "mode": mode_name,
        "prompt_dir": str(prompt_dir),
        "index": str(index_path),
        "preflight": preflight_payload,
        **record,
        "instructions": instructions or [],
    }
    if include_prompt:
        payload["prompt"] = prompt
    return payload


def print_payload(payload: dict) -> int:
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("ok") else 1
