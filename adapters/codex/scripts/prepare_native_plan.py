#!/usr/bin/env python3
"""Prepare a Codex native subagent spawn plan for every task card in a state dir."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
CREATE_TASK_CARDS = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "create_task_cards.py"
EXAMPLE_REVIEW_SKILL = "example-review-skill"

sys.path.insert(0, str(SCRIPT_DIR))
from prepare_native_subagent import prepare  # noqa: E402


def skill_items(skill_names: list[str]) -> list[dict]:
    return [{"type": "skill", "name": name} for name in skill_names if name]


def spawn_agent_payload(payload: dict) -> dict:
    skills = payload.get("may_use_skills", []) or []
    return {
        "agent_type": payload["agent_type"],
        "fork_context": False,
        "items": [
            *skill_items(skills),
            {
                "type": "text",
                "text": f"Read and follow this Codex native subagent prompt exactly: {payload['prompt_path']}",
            },
        ],
        "message_source": payload["prompt_path"],
        "lifecycle": [
            "spawn_agent",
            "wait_agent",
            "send_input_once_if_reports_missing",
            "collect_result_reports",
            "close_agent",
        ],
    }


def discover_cards(state_dir: Path, role: str | None) -> list[Path]:
    tasks_dir = state_dir / "tasks"
    cards = sorted(tasks_dir.glob("*.md"))
    if not role:
        return cards
    needle = f"role: {role.lower()}"
    selected: list[Path] = []
    for card in cards:
        text = card.read_text(encoding="utf-8", errors="replace").lower()
        if needle in text:
            selected.append(card)
    return selected


def write_plan(out_dir: Path, records: list[dict]) -> Path:
    plan_path = out_dir / "spawn-plan.md"
    lines = [
        "# Codex Native Spawn Plan",
        "",
        "Main Codex uses this as the dispatch checklist. Spawn each task with the listed agent type and prompt file.",
        "",
        "| Order | Task | Role | Agent type | Skills | Prompt |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for index, item in enumerate(records, start=1):
        skills = ", ".join(item.get("may_use_skills") or []) or "none"
        lines.append(
            f"| {index} | `{item['task_id']}` | {item['role']} | `{item['agent_type']}` | "
            f"{skills} | `{Path(item['prompt_path']).name}` |"
        )
    lines.extend(
        [
            "",
            "After all spawned agents finish:",
            "",
            "1. Wait for every spawned agent with `wait_agent`.",
            "2. If required reports are missing, use `send_input` once with the missing evidence request.",
            "3. Collect result JSON and Markdown reports.",
            "4. Close each completed/blocked/failed agent with `close_agent` so it does not occupy concurrency slots.",
            "5. Run `adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync`.",
            "6. Capture changed files (incl. untracked) with `adapters/openclaw/scripts/capture_changed_files.py --state-dir .codex-multi-agent`.",
            "7. Run `adapters/openclaw/scripts/audit_worker_output.py --write-audit`.",
            "8. Deliver only after result reports and ownership audit pass.",
        ]
    )
    plan_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return plan_path


def build_plan(state_dir: Path, out_dir: Path | None, role: str | None, skip_preflight: bool) -> dict:
    state = state_dir.resolve()
    cards = discover_cards(state, role)
    native_dir = (out_dir or state / "native-subagents").resolve()
    native_dir.mkdir(parents=True, exist_ok=True)
    if not cards:
        return {"ok": False, "error": f"no task cards found in {state / 'tasks'}", "state_dir": str(state)}

    records: list[dict] = []
    failures: list[dict] = []
    for card in cards:
        payload = prepare(card, state, native_dir, skip_preflight=skip_preflight, include_prompt=False)
        if payload.get("ok"):
            spawn_payload = spawn_agent_payload(payload)
            records.append(
                {
                    "task_id": payload["task_id"],
                    "session_name": payload["session_name"],
                    "role": payload["role"],
                    "agent_type": payload["agent_type"],
                    "workspace_root": payload["workspace_root"],
                    "task_card": payload["task_card"],
                    "prompt_path": payload["prompt_path"],
                    "result_json": payload["result_json"],
                    "result_markdown": payload["result_markdown"],
                    "may_use_skills": payload.get("may_use_skills", []),
                    "spawn_instruction": payload["spawn_instruction"],
                    "spawn_agent_payload": spawn_payload,
                }
            )
        else:
            failures.append({"task_card": str(card), "payload": payload})

    plan_path = write_plan(native_dir, records)
    return {
        "ok": not failures,
        "runtime": "codex-native",
        "mode": "native-spawn-plan",
        "state_dir": str(state),
        "native_dir": str(native_dir),
        "plan_path": str(plan_path),
        "count": len(records),
        "records": records,
        "failures": failures,
        "main_instructions": [
            "Spawn one Codex native subagent per record using spawn_agent_payload.",
            "Track agent_id for wait_agent/send_input/close_agent lifecycle.",
            "Attach or name only skills listed in may_use_skills; spawn_agent_payload.items includes skill items when present.",
            "Wait for JSON and Markdown result reports before gate sync.",
            "Close completed agents after collecting their reports.",
            "Run gate sync and scope audit before final delivery.",
        ],
    }


def run_self_check() -> int:
    with tempfile.TemporaryDirectory(prefix="codex-native-plan-") as tmp:
        tmp_path = Path(tmp)
        state_dir = tmp_path / ".codex-multi-agent"
        proc = subprocess.run(
            [
                sys.executable,
                str(CREATE_TASK_CARDS),
                "--task",
                "Native spawn plan self-check",
                "--mode",
                "implement",
                "--modules",
                "docs",
                "--runtime",
                "codex",
                "--review-skill",
                EXAMPLE_REVIEW_SKILL,
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
        payload = build_plan(state_dir, tmp_path / "native", role=None, skip_preflight=False)
        if not payload.get("ok") or payload.get("count", 0) < 3:
            print(json.dumps({"ok": False, "stage": "build_plan", "payload": payload}, indent=2))
            return 1
        agent_types = {item["agent_type"] for item in payload["records"]}
        if "multi-agent-worker" not in agent_types or "multi-agent-reviewer" not in agent_types:
            print(json.dumps({"ok": False, "error": "missing worker/reviewer agent mappings", "agent_types": sorted(agent_types)}, indent=2))
            return 1
        reviewer_records = [item for item in payload["records"] if item.get("agent_type") == "multi-agent-reviewer"]
        if not reviewer_records:
            print(json.dumps({"ok": False, "error": "no reviewer record"}, indent=2))
            return 1
        reviewer_items = reviewer_records[0].get("spawn_agent_payload", {}).get("items", [])
        if not any(item.get("type") == "skill" and item.get("name") == EXAMPLE_REVIEW_SKILL for item in reviewer_items):
            print(json.dumps({"ok": False, "error": "reviewer spawn_agent_payload should include example review skill item"}, indent=2))
            return 1
        plan_path = Path(payload["plan_path"])
        if "Codex Native Spawn Plan" not in plan_path.read_text(encoding="utf-8"):
            print(json.dumps({"ok": False, "error": "plan markdown missing title"}, indent=2))
            return 1
        print(json.dumps({"ok": True, "adapter": "codex-native-plan", "plan": str(plan_path), "count": payload["count"]}, indent=2))
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=".codex-multi-agent", help="Mission-control dir containing tasks/")
    parser.add_argument("--out", help="Native prompt output dir (default: <state-dir>/native-subagents)")
    parser.add_argument("--role", choices=["Explorer", "Worker", "Reviewer", "Verifier"], help="Only prepare one role")
    parser.add_argument("--skip-preflight", action="store_true", help="Write prompts even if preflight cannot run")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    payload = build_plan(
        Path(args.state_dir).expanduser().resolve(),
        Path(args.out).expanduser().resolve() if args.out else None,
        args.role,
        args.skip_preflight,
    )
    print(json.dumps(payload, indent=2))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
