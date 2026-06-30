#!/usr/bin/env python3
"""Codex App dogfood checks for native subagent readiness and Worker smoke evidence."""

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
PREPARE_NATIVE_PLAN = SCRIPT_DIR / "prepare_native_plan.py"
PREPARE_NATIVE_SUBAGENT = SCRIPT_DIR / "prepare_native_subagent.py"


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def validate_worker_smoke(state_dir: Path) -> dict:
    marker = state_dir / "dogfood" / "worker-smoke.txt"
    result_json = state_dir / "results" / "T900-worker-smoke.json"
    result_md = state_dir / "results" / "T900-worker-smoke.md"
    errors: list[str] = []

    if not marker.is_file():
        errors.append(f"missing marker: {marker}")
    elif marker.read_text(encoding="utf-8").strip() != "worker-smoke-ok":
        errors.append("marker content is not worker-smoke-ok")

    payload: dict = {}
    if not result_json.is_file():
        errors.append(f"missing JSON report: {result_json}")
    else:
        try:
            payload = json.loads(result_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON report: {exc}")

    if not result_md.is_file():
        errors.append(f"missing Markdown report: {result_md}")

    if payload:
        if payload.get("role") != "Worker":
            errors.append("JSON role is not Worker")
        if payload.get("status") != "completed":
            errors.append("JSON status is not completed")
        if payload.get("required_paths_verified") is not True:
            errors.append("required_paths_verified is not true")
        changed = [str(item).replace("\\", "/") for item in payload.get("files_changed", [])]
        outside = [
            item
            for item in changed
            if not item.startswith(".codex-multi-agent/dogfood-worker-smoke/dogfood/")
            and not item.startswith(".codex-multi-agent/dogfood-worker-smoke/results/")
        ]
        if outside:
            errors.append(f"files_changed outside dogfood scope: {outside}")

    return {
        "ok": not errors,
        "state_dir": str(state_dir),
        "marker": str(marker),
        "result_json": str(result_json),
        "result_markdown": str(result_md),
        "errors": errors,
    }


def native_plan_self_check() -> dict:
    with tempfile.TemporaryDirectory(prefix="codex-app-dogfood-") as tmp:
        state_dir = Path(tmp) / ".codex-multi-agent"
        create = run(
            [
                sys.executable,
                str(CREATE_TASK_CARDS),
                "--task",
                "Codex App dogfood native plan",
                "--mode",
                "implement",
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
            ]
        )
        if create.returncode != 0:
            return {"ok": False, "stage": "create_task_cards", "output": create.stderr or create.stdout}
        plan = run([sys.executable, str(PREPARE_NATIVE_PLAN), "--state-dir", str(state_dir)])
        if plan.returncode != 0:
            return {"ok": False, "stage": "prepare_native_plan", "output": plan.stderr or plan.stdout}
        payload = json.loads(plan.stdout)
        agent_types = {item.get("agent_type") for item in payload.get("records", [])}
        needed = {"multi-agent-worker", "multi-agent-reviewer"}
        missing = sorted(needed - agent_types)
        reviewer_records = [item for item in payload.get("records", []) if item.get("agent_type") == "multi-agent-reviewer"]
        reviewer_items = reviewer_records[0].get("spawn_agent_payload", {}).get("items", []) if reviewer_records else []
        has_ssrd_skill_item = any(item.get("type") == "skill" and item.get("name") == "ssrd" for item in reviewer_items)
        return {
            "ok": not missing and has_ssrd_skill_item and payload.get("ok") is True,
            "stage": "native_plan",
            "count": payload.get("count", 0),
            "agent_types": sorted(agent_types),
            "missing_agent_types": missing,
            "reviewer_has_ssrd_skill_item": has_ssrd_skill_item,
        }


def legacy_result_path_self_check() -> dict:
    with tempfile.TemporaryDirectory(prefix="codex-legacy-result-path-") as tmp:
        tmp_path = Path(tmp)
        state_dir = tmp_path / ".codex-multi-agent"
        tasks_dir = state_dir / "tasks"
        dogfood = state_dir / "dogfood"
        results = state_dir / "results"
        tasks_dir.mkdir(parents=True)
        dogfood.mkdir(parents=True)
        results.mkdir(parents=True)
        card = tasks_dir / "T900-worker-smoke.md"
        card.write_text(
            "\n".join(
                [
                    "task_id: T900",
                    "session_name: worker-smoke",
                    "role: Worker",
                    "title: Worker smoke",
                    "objective: Verify legacy result path parsing",
                    f"workspace_root: {tmp_path}",
                    "write_permission: true",
                    "allowed_paths:",
                    "  - .codex-multi-agent/dogfood/**",
                    "required_paths:",
                    "  - .codex-multi-agent/dogfood",
                    "may_use_skills:",
                    "  []",
                    f"result_json_path: {results / 'T900-worker-smoke.json'}",
                    f"result_markdown_path: {results / 'T900-worker-smoke.md'}",
                    "",
                    "--- TASK CARD ---",
                    "Write dogfood marker.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        proc = run([sys.executable, str(PREPARE_NATIVE_SUBAGENT), "--task-card", str(card), "--state-dir", str(state_dir)])
        if proc.returncode != 0:
            return {"ok": False, "stage": "prepare_native_subagent", "output": proc.stderr or proc.stdout}
        payload = json.loads(proc.stdout)
        prompt_text = Path(payload["prompt_path"]).read_text(encoding="utf-8")
        ok = bool(payload.get("result_json")) and bool(payload.get("result_markdown")) and "JSON:" in prompt_text
        return {
            "ok": ok,
            "stage": "legacy_result_path",
            "result_json": payload.get("result_json"),
            "result_markdown": payload.get("result_markdown"),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="Run deterministic native-plan and parser checks")
    parser.add_argument("--worker-smoke-state", help="Validate an existing Codex App Worker smoke state dir")
    args = parser.parse_args()

    checks: list[dict] = []
    if args.self_check:
        checks.extend([native_plan_self_check(), legacy_result_path_self_check()])
    if args.worker_smoke_state:
        checks.append(validate_worker_smoke(Path(args.worker_smoke_state).expanduser().resolve()))
    if not checks:
        parser.error("use --self-check and/or --worker-smoke-state")

    payload = {"ok": all(item.get("ok") for item in checks), "checks": checks}
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
