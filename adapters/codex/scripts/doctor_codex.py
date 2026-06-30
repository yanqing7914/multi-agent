#!/usr/bin/env python3
"""Codex-only readiness doctor for the multi-agent entrypoint."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ADAPTER_ROOT = SCRIPT_DIR.parent
REPO_ROOT = ADAPTER_ROOT.parent.parent


def exists(path: Path) -> bool:
    return path.exists()


def check() -> dict:
    home = Path.home()
    root_skill_paths = [
        home / ".codex" / "skills" / "multi-agent-coding" / "SKILL.md",
        home / ".codex" / "skills" / "multi-agent" / "SKILL.md",
        home / ".agents" / "skills" / "multi-agent-coding" / "SKILL.md",
        home / ".agents" / "skills" / "multi-agent" / "SKILL.md",
    ]
    codex_adapter_paths = [
        home / ".agents" / "skills" / "codex-multi-agent" / "SKILL.md",
        home / ".codex" / "skills" / "codex-multi-agent" / "SKILL.md",
    ]
    expected_agents = [
        home / ".codex" / "agents" / "multi-agent-worker.toml",
        home / ".codex" / "agents" / "multi-agent-reviewer.toml",
    ]
    required_repo_files = [
        REPO_ROOT / "SKILL.md",
        ADAPTER_ROOT / "SKILL.md",
        ADAPTER_ROOT / "NATIVE_SUBAGENT_CONTRACT.md",
        REPO_ROOT / "scripts" / "run_multi_agent.py",
        REPO_ROOT / "scripts" / "install_native_skills.py",
        REPO_ROOT / "adapters" / "openclaw" / "scripts" / "create_task_cards.py",
        REPO_ROOT / "adapters" / "openclaw" / "scripts" / "audit_worker_output.py",
        SCRIPT_DIR / "prepare_native_subagent.py",
        SCRIPT_DIR / "prepare_native_plan.py",
        SCRIPT_DIR / "dogfood_codex_app.py",
        SCRIPT_DIR / "finalize_native_run.py",
        SCRIPT_DIR / "launch_codex_worker.sh",
    ]
    worker_smoke_state = REPO_ROOT / ".codex-multi-agent" / "dogfood-worker-smoke"
    worker_smoke_marker = worker_smoke_state / "dogfood" / "worker-smoke.txt"
    worker_smoke_json = worker_smoke_state / "results" / "T900-worker-smoke.json"

    root_skill_installed = [str(path) for path in root_skill_paths if exists(path)]
    codex_skill_installed = [str(path) for path in codex_adapter_paths if exists(path)]
    agent_files = [str(path) for path in expected_agents if exists(path)]
    repo_files = [str(path) for path in required_repo_files if exists(path)]
    missing_repo_files = [str(path) for path in required_repo_files if not exists(path)]
    codex_bin = shutil.which("codex")

    ready = bool(repo_files) and not missing_repo_files and len(agent_files) == len(expected_agents)
    app_ready = ready and (bool(root_skill_installed) or bool(codex_skill_installed) or (REPO_ROOT / "SKILL.md").is_file())

    next_steps: list[str] = []
    if len(agent_files) != len(expected_agents):
        next_steps.append("Run: python scripts/install_native_skills.py --client codex --scope primary --force")
    if not root_skill_installed:
        next_steps.append("Install the root multi-agent entrypoint if you want multi-agent itself to be the Codex trigger.")
    if not codex_bin:
        next_steps.append("Optional: install Codex CLI for scripted bridge mode; Codex App native subagents can still work without it.")
    if not missing_repo_files and len(agent_files) == len(expected_agents):
        next_steps.append("Use multi-agent in Codex; it should take the Codex fast path and spawn Worker/Reviewer roles.")

    return {
        "ok": True,
        "client": "codex",
        "repo_root": str(REPO_ROOT),
        "root_entry_installed": bool(root_skill_installed),
        "root_entry_paths": root_skill_installed,
        "codex_adapter_installed": bool(codex_skill_installed),
        "codex_adapter_paths": codex_skill_installed,
        "custom_agents_ready": len(agent_files) == len(expected_agents),
        "custom_agent_paths": agent_files,
        "missing_custom_agents": [str(path) for path in expected_agents if not exists(path)],
        "codex_cli": {"present": bool(codex_bin), "path": codex_bin},
        "repo_files_ready": not missing_repo_files,
        "repo_files": repo_files,
        "missing_repo_files": missing_repo_files,
        "codex_fast_path_ready": app_ready,
        "worker_smoke_ready": worker_smoke_marker.is_file()
        and worker_smoke_marker.read_text(encoding="utf-8").strip() == "worker-smoke-ok"
        and worker_smoke_json.is_file(),
        "worker_smoke_state": str(worker_smoke_state),
        "worker_smoke_note": "optional dogfood evidence; MISS means not run in this checkout, not that native workers are unavailable",
        "recommended_runtime_order": ["codex-native-plan", "codex-native", "codex", "codex-desktop"],
        "codex_app_modes": {
            "native_spawn_plan": "scripts/run_multi_agent.py --runtime codex-native-plan --state-dir .codex-multi-agent",
            "single_native_spawn": "scripts/run_multi_agent.py --runtime codex-native --task-card <card>",
            "manual_handoff": "scripts/run_multi_agent.py --runtime codex-desktop --task-card <card>",
        },
        "next_steps": next_steps,
    }


def render(payload: dict) -> str:
    mark = lambda value: "OK" if value else "MISS"
    lines = [
        "Codex multi-agent doctor",
        f"- repo: {payload['repo_root']}",
        f"- root multi-agent entry: {mark(payload['root_entry_installed'])}",
        f"- codex adapter entry: {mark(payload['codex_adapter_installed'])}",
        f"- custom agents: {mark(payload['custom_agents_ready'])}",
        f"- codex CLI bridge: {mark(payload['codex_cli']['present'])}",
        f"- repo scripts: {mark(payload['repo_files_ready'])}",
        f"- Codex fast path ready: {mark(payload['codex_fast_path_ready'])}",
        f"- Worker smoke evidence: {mark(payload['worker_smoke_ready'])}  ({payload['worker_smoke_note']})",
        "- runtime order: codex-native-plan -> codex-native -> codex -> codex-desktop",
        "- next steps:",
    ]
    lines.extend(f"  - {step}" for step in payload["next_steps"])
    return "\n".join(lines)


def self_check() -> int:
    payload = check()
    required_keys = {
        "root_entry_installed",
        "codex_adapter_installed",
        "custom_agents_ready",
        "codex_cli",
        "repo_files_ready",
        "codex_fast_path_ready",
        "worker_smoke_ready",
        "recommended_runtime_order",
        "codex_app_modes",
    }
    missing = sorted(required_keys - set(payload))
    if missing:
        print(json.dumps({"ok": False, "missing_keys": missing}, indent=2))
        return 1
    if payload["recommended_runtime_order"] != ["codex-native-plan", "codex-native", "codex", "codex-desktop"]:
        print(json.dumps({"ok": False, "error": "runtime order changed"}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "codex doctor self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return self_check()

    payload = check()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(render(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
