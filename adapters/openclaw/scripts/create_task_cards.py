#!/usr/bin/env python3
"""Create OpenClaw multi-agent task cards and ownership metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from _runtimes import TASK_CARD_RUNTIME_CHOICES

DEFAULT_BLOCKED_PATHS = [
    ".env",
    ".env.*",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "~/.ssh/**",
    "~/.codex/auth.json",
    "**/*.pem",
    "**/*.key",
]

DEFAULT_BLOCKED_COMMANDS = [
    "npm install",
    "pnpm install",
    "git push",
    "git reset --hard",
    "deploy",
    "publish",
]

MODULE_PATHS = {
    "backend": ["server/**", "backend/**", "api/**"],
    "frontend": ["client/**", "frontend/**", "web/**", "src/**"],
    "tests": ["tests/**", "test/**", "__tests__/**", "**/*.test.*", "**/*.spec.*"],
    "docs": ["docs/**", "README.md"],
    "openclaw_adapter": ["adapters/openclaw/**"],
}

PREFLIGHT_GUIDANCE = (
    "Preflight (required first step): cd to workspace_root (absolute target_repo path below) before "
    "any reads or edits; run pwd; run preflight_command; confirm each required_paths entry exists. "
    "If OpenClaw ignores sessions_spawn cwd, you MUST cd using the absolute workspace_root. If any "
    "required path is missing, set status=blocked, required_paths_verified=false, list missing paths, "
    "keep files_changed empty, and do not fake review or edits on unread files."
)

WORKSPACE_GUIDANCE = (
    "Record workspace_observed (output of pwd after cd) and list every file you actually read in "
    "files_read. Do not set required_paths_verified=true with an empty files_read when required_paths "
    "lists concrete directories."
)

ROLE_CONSTRAINTS = {
    "Explorer": {
        "write_permission": False,
        "may_spawn_sessions": False,
        "execution_guidance": [
            "Read-only: investigate code and report evidence; do not edit files.",
            "Use rg/find/ls only; stop if you need write access or blocked paths.",
            "Return findings with file paths and line references when possible.",
        ],
    },
    "Worker": {
        "write_permission": True,
        "may_spawn_sessions": False,
        "execution_guidance": [
            "Edit only within allowed_paths; never touch blocked_paths or secrets.",
            "files_changed must list only business code you edited — do NOT list your own result report files under .codex-multi-agent/results/.",
            "Do not install dependencies, deploy, push, or run blocked_commands.",
            "Stop and report blockers instead of expanding scope.",
            "Write both result report files listed in result_report_paths before completion_signal.",
        ],
    },
    "Reviewer": {
        "write_permission": False,
        "may_spawn_sessions": False,
        "execution_guidance": [
            "Read-only review: do not edit files or spawn sessions.",
            "Use authorized review skills only via may_use_skills.",
            "Report findings by severity with evidence; files_changed must stay empty.",
        ],
    },
    "Verifier": {
        "write_permission": False,
        "may_spawn_sessions": False,
        "execution_guidance": [
            "Run allowed validation commands only; do not modify code unless assigned as Worker.",
            "List every file you opened or inspected in files_read; pytest or test pass alone is not evidence.",
            "Do not set required_paths_verified=true with an empty files_read when required_paths lists concrete directories.",
            "Record commands_run and validation results in the result report.",
        ],
    },
}

GATE_BY_ROLE = {
    "Explorer": "explorers_complete",
    "Worker": "workers_complete",
    "Reviewer": "review_complete",
    "Verifier": "verify_complete",
}

DEFAULT_TOOLS_BY_ROLE = {
    "Explorer": ["repo_index_tool", "shell_tool"],
    "Worker": ["git_tool", "repo_index_tool", "test_runner_tool", "lint_tool", "shell_tool"],
    "Reviewer": ["repo_index_tool", "git_tool"],
    "Verifier": ["test_runner_tool", "lint_tool", "git_tool", "shell_tool"],
}

ROLE_ORDER = ("Explorer", "Worker", "Reviewer", "Verifier")

SCRIPT_DIR = Path(__file__).resolve().parent
ADAPTER_ROOT = SCRIPT_DIR.parent
REPO_ROOT = ADAPTER_ROOT.parent.parent


def adapter_required_path() -> str:
    return "adapters/openclaw" if (REPO_ROOT / "adapters" / "openclaw").exists() else "."


def adapter_script(name: str) -> str:
    return str((SCRIPT_DIR / name).resolve())


def python_invocation() -> str:
    return sys.executable


def task_id(index: int) -> str:
    return f"T{index:03d}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def result_paths(state_dir: Path, task: dict) -> dict[str, str]:
    stem = f"{task['task_id']}-{task['session_name']}"
    results_dir = state_dir / "results"
    return {
        "json": str(results_dir / f"{stem}.json"),
        "markdown": str(results_dir / f"{stem}.md"),
    }


def parse_simple_yaml(text: str) -> dict:
    """Parse the small flat YAML files used in examples/ (dependency-free)."""
    text = text.lstrip("\ufeff")
    data: dict = {}
    current_list_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if re.match(r"^\s+- ", line) and current_list_key:
            data.setdefault(current_list_key, []).append(line.strip()[2:].strip())
            continue
        current_list_key = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            current_list_key = key
            data.setdefault(key, [])
            continue
        data[key] = value.strip('"').strip("'")
    return data


def parse_modules_yaml_section(text: str) -> list[dict] | None:
    """Parse modules with optional per-module paths (nested YAML list items)."""
    text = text.lstrip("\ufeff")
    in_modules = False
    modules_indent: int | None = None
    current: dict | None = None
    current_paths_key: str | None = None
    specs: list[dict] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if stripped.startswith("modules:") and not stripped.startswith("modules:" + " "):
            in_modules = True
            modules_indent = indent
            current = None
            current_paths_key = None
            continue

        if not in_modules:
            continue

        if modules_indent is not None and indent <= modules_indent and not stripped.startswith("- "):
            break

        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item.startswith("name:"):
                if current and current.get("name"):
                    specs.append(current)
                current = {"name": item.split(":", 1)[1].strip().strip('"').strip("'"), "paths": None}
                current_paths_key = None
                continue
            if current is None:
                current = {"name": item.strip('"').strip("'"), "paths": None}
                current_paths_key = None
                continue
            if current_paths_key == "paths":
                current.setdefault("paths", []).append(item.strip('"').strip("'"))
            continue

        if current is not None and ":" in stripped:
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key == "name":
                current["name"] = value
            elif key == "paths" and not value:
                current_paths_key = "paths"
                current["paths"] = []
            continue

    if current and current.get("name"):
        specs.append(current)

    return specs if specs else None


def normalize_module_specs(raw_modules: object) -> list[dict]:
    """Normalize CLI/YAML/JSON modules into [{name, paths?}, ...]."""
    specs: list[dict] = []
    if raw_modules is None:
        return specs
    if isinstance(raw_modules, str):
        raw_modules = [raw_modules]
    if not isinstance(raw_modules, list):
        return specs
    for item in raw_modules:
        if isinstance(item, str):
            specs.append({"name": item.strip(), "paths": None})
        elif isinstance(item, dict):
            name = item.get("name") or item.get("module")
            if not name:
                continue
            paths = item.get("paths")
            if paths is not None and not isinstance(paths, list):
                paths = [paths]
            specs.append({"name": str(name).strip(), "paths": paths})
    return specs


def resolve_module_paths(name: str, explicit_paths: list[str] | None = None) -> tuple[list[str], list[str]]:
    """Return (allowed_paths, warnings) for a module name."""
    warnings: list[str] = []
    if explicit_paths:
        return list(explicit_paths), warnings
    if name in MODULE_PATHS:
        return list(MODULE_PATHS[name]), warnings
    default = [f"{name}/**"]
    warnings.append(
        f"module '{name}' has no explicit paths: using default {default!r}. "
        f"Supply paths: per module in YAML/JSON, e.g. modules: [{{name: {name}, paths: [src/**, tests/**]}}]"
    )
    return default, warnings


def module_allowed_paths(module: str, explicit_paths: list[str] | None = None) -> list[str]:
    paths, _ = resolve_module_paths(module, explicit_paths)
    return paths


def required_paths_for_task(task: dict, all_tasks: list[dict]) -> list[str]:
    allowed = task.get("allowed_paths", [])
    if allowed == ["**/*"]:
        module_paths: list[str] = []
        for item in all_tasks:
            if not item.get("module"):
                continue
            for p in item.get("allowed_paths", []) or []:
                if p in {"**/*", "**"}:
                    continue
                module_paths.append(p)
        if module_paths:
            return sorted(dict.fromkeys(module_paths))
    return list(allowed)


def resolve_workspace_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return Path.cwd().resolve()


def preflight_commands(workspace_root: Path, required_paths: list[str]) -> list[str]:
    root = str(workspace_root)
    verify_script = adapter_script("verify_workspace.py")
    py = python_invocation()
    paths_arg = " ".join(f'"{item}"' for item in required_paths if item not in {"**/*", "**"})
    lines = [
        f'cd "{root}" && pwd',
    ]
    if paths_arg:
        lines.append(
            f'{py} "{verify_script}" --workspace-root "{root}" --required-paths {paths_arg}'
        )
    else:
        lines.append(f'{py} "{verify_script}" --workspace-root "{root}"')
    return lines


def execution_guidance_for_task(role: str) -> list[str]:
    constraints = ROLE_CONSTRAINTS.get(role, ROLE_CONSTRAINTS["Worker"])
    return [PREFLIGHT_GUIDANCE, WORKSPACE_GUIDANCE, *constraints["execution_guidance"]]


def prerequisite_ids(tasks: list[dict], task: dict) -> list[str]:
    role = task["role"]
    module = task.get("module")
    prereqs: list[str] = []
    if role == "Worker" and module:
        for item in tasks:
            if item.get("module") == module and item.get("role") == "Explorer":
                prereqs.append(item["task_id"])
    if role == "Reviewer":
        prereqs.extend(item["task_id"] for item in tasks if item.get("role") == "Worker")
    if role == "Verifier":
        prereqs.extend(item["task_id"] for item in tasks if item.get("role") == "Reviewer")
    return prereqs


def main_commands_for_task(
    state_dir: Path,
    task: dict,
    all_tasks: list[dict],
    workspace_root: Path,
) -> dict[str, list[str]]:
    rel_state = str(state_dir)
    py = python_invocation()
    status_script = f'{py} "{adapter_script("update_task_status.py")}"'
    audit_script = f'{py} "{adapter_script("audit_worker_output.py")}"'
    role = task["role"]
    task_id_value = task["task_id"]
    session = task["session_name"]
    required = task.get("required_paths") or required_paths_for_task(task, all_tasks)

    before_spawn = [
        f"{status_script} --state-dir {rel_state} --sync",
        "# Subagent preflight (must run inside child session before work):",
        *preflight_commands(workspace_root, required),
    ]
    prereqs = prerequisite_ids(all_tasks, task)
    if prereqs:
        before_spawn.append(
            f"# Gate check: prerequisite tasks must be completed -> {', '.join(prereqs)}"
        )

    after_result = [
        f"{status_script} --state-dir {rel_state} --task-id {task_id_value} --status completed",
        f"{status_script} --state-dir {rel_state} --sync",
    ]

    if role == "Worker":
        after_result.extend(
            [
                f"git diff --name-only > {rel_state}/changed-files.txt",
                (
                    f"{audit_script} --ownership {rel_state}/ownership.json "
                    f"--results {rel_state}/results "
                    f"--changed-files {rel_state}/changed-files.txt "
                    f"--write-audit --state-dir {rel_state}"
                ),
            ]
        )
    if role == "Verifier":
        after_result.append(f"{status_script} --state-dir {rel_state} --summarize")

    return {
        "before_spawn": before_spawn,
        "spawn": [f'sessions_spawn name="{session}" runtime="{task["runtime"]}"'],
        "send": [f'sessions_send session="{session}" message="<paste this task card>"'],
        "yield": [f'sessions_yield session="{session}" when="waiting for result report"'],
        "after_result": after_result,
    }


def tools_for_task(task: dict) -> list[str]:
    declared = task.get("tools_used")
    if isinstance(declared, list) and declared:
        return declared
    return list(DEFAULT_TOOLS_BY_ROLE.get(task.get("role", "Worker"), []))


def memory_context_tail(workspace_root: Path, lines: int = 8) -> str:
    memory_path = workspace_root / "MEMORY.md"
    if not memory_path.exists():
        return "Generated by create_task_cards.py"
    content = memory_path.read_text(encoding="utf-8").splitlines()
    tail = [line for line in content if line.strip() and not line.startswith("#")][-lines:]
    if not tail:
        return "Generated by create_task_cards.py"
    return "Generated by create_task_cards.py\n\nRecent project memory:\n" + "\n".join(tail)


def write_card(
    path: Path,
    task: dict,
    state_dir: Path,
    all_tasks: list[dict],
    workspace_root: Path,
) -> None:
    role = task["role"]
    constraints = ROLE_CONSTRAINTS.get(role, ROLE_CONSTRAINTS["Worker"])
    report_paths = result_paths(state_dir, task)
    prereqs = prerequisite_ids(all_tasks, task)
    gate_id = GATE_BY_ROLE.get(role, "final_delivery")
    commands = main_commands_for_task(state_dir, task, all_tasks, workspace_root)
    required_paths = task.get("required_paths") or required_paths_for_task(task, all_tasks)
    guidance = execution_guidance_for_task(role)
    target_repo = task.get("target_repo", str(workspace_root))
    preflight = preflight_commands(workspace_root, required_paths)
    context_block = task.get("context") or memory_context_tail(workspace_root)
    tools_used = tools_for_task(task)

    lines = [
        f"task_id: {task['task_id']}",
        f"session_name: {task['session_name']}",
        f"runtime: {task['runtime']}",
        f"mode: {task['mode']}",
        f"role: {role}",
        f"title: {task['title']}",
        f"objective: {task['objective']}",
        f"context: {context_block.replace(chr(10), ' ')}",
        "tools_used:",
    ]
    lines.extend(f"  - {item}" for item in tools_used)
    lines.extend(
        [
            f"workspace_root: {workspace_root}",
            f"target_repo: {target_repo}",
            "workspace_note: OpenClaw may ignore sessions_spawn cwd — child MUST cd to workspace_root (absolute) before reading files.",
            "dependencies:",
        ]
    )
    if prereqs:
        lines.extend(f"  - {item}" for item in prereqs)
    else:
        lines.append("  []")
    lines.extend(
        [
            f"write_permission: {'true' if constraints['write_permission'] else 'false'}",
            "allowed_paths:",
        ]
    )
    lines.extend(f"  - {item}" for item in task["allowed_paths"])
    lines.append("required_paths:")
    lines.extend(f"  - {item}" for item in required_paths)
    lines.append("preflight_command:")
    lines.extend(f"  - {item}" for item in preflight)
    lines.append("blocked_paths:")
    lines.extend(f"  - {item}" for item in task["blocked_paths"])
    lines.append("allowed_commands:")
    lines.extend(f"  - {item}" for item in task["allowed_commands"])
    lines.append("blocked_commands:")
    lines.extend(f"  - {item}" for item in task["blocked_commands"])
    lines.append("may_use_skills:")
    if task["may_use_skills"]:
        lines.extend(f"  - {item}" for item in task["may_use_skills"])
    else:
        lines.append("  []")
    lines.append(f"may_spawn_sessions: {'true' if constraints['may_spawn_sessions'] else 'false'}")
    lines.append("validation_required:")
    lines.extend(f"  - {item}" for item in task["validation_required"])
    lines.append("execution_guidance:")
    lines.extend(f"  - {item}" for item in guidance)
    lines.extend(
        [
            "stop_conditions:",
            "  - Need to edit outside allowed_paths",
            "  - Required paths missing in workspace (set status=blocked; do not fake completion)",
            "  - Need secret or credential access",
            "  - Need dependency installation",
            "  - Need deployment or production mutation",
            "  - User changes may be overwritten",
            "gate:",
            f"  id: {gate_id}",
            f"  unblocks: {task.get('unblocks', 'next role phase')}",
            "  pass_when:",
            "    - result_report_paths.json exists",
            "    - status is completed only after required_paths were visible/readable (required_paths_verified=true)",
            "    - status is blocked with handoff_notes when required paths were missing",
            "result_report_paths:",
            f"  json: {report_paths['json']}",
            f"  markdown: {report_paths['markdown']}",
            "main_commands:",
            "  before_spawn:",
        ]
    )
    lines.extend(f"    - {item}" for item in commands["before_spawn"])
    lines.append("  spawn:")
    lines.extend(f"    - {item}" for item in commands["spawn"])
    lines.append("  send:")
    lines.extend(f"    - {item}" for item in commands["send"])
    lines.append("  yield:")
    lines.extend(f"    - {item}" for item in commands["yield"])
    lines.append("  after_result:")
    lines.extend(f"    - {item}" for item in commands["after_result"])
    lines.extend(
        [
            "openclaw_handoff:",
            f"  spawn: {commands['spawn'][0]}",
            f"  send: {commands['send'][0]}",
            f"  yield: {commands['yield'][0]}",
            f"completion_signal: \"<task_complete task_id='{task['task_id']}' status='completed'>\"",
            "output_format: result-report.md + companion JSON",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def build_tasks(args: argparse.Namespace) -> tuple[list[dict], list[str]]:
    tasks: list[dict] = []
    warnings: list[str] = []
    index = 1

    module_specs = normalize_module_specs(getattr(args, "module_specs", None) or args.modules)

    for spec in module_specs:
        module = spec["name"]
        allowed_paths, path_warnings = resolve_module_paths(module, spec.get("paths"))
        warnings.extend(path_warnings)
        explorer = {
            "task_id": task_id(index),
            "session_name": f"explorer-{module}",
            "runtime": args.runtime,
            "mode": "research" if args.mode != "review" else "review",
            "role": "Explorer",
            "module": module,
            "title": f"Explore {module}",
            "objective": f"Research {module} for: {args.task}",
            "allowed_paths": allowed_paths,
            "blocked_paths": DEFAULT_BLOCKED_PATHS,
            "allowed_commands": ["rg", "find", "ls"],
            "blocked_commands": DEFAULT_BLOCKED_COMMANDS,
            "may_use_skills": [],
            "validation_required": ["Report findings with file evidence"],
            "unblocks": f"worker-{module}",
            "status": "pending",
        }
        tasks.append(explorer)
        index += 1

        if args.mode in {"implement", "refactor", "fix"}:
            worker = {
                "task_id": task_id(index),
                "session_name": f"worker-{module}",
                "runtime": args.runtime,
                "mode": args.mode,
                "role": "Worker",
                "module": module,
                "title": f"Implement {module}",
                "objective": f"Implement the {module} portion of: {args.task}",
                "allowed_paths": allowed_paths,
                "blocked_paths": DEFAULT_BLOCKED_PATHS,
                "allowed_commands": ["rg", "npm test", "pnpm test", "pytest"],
                "blocked_commands": DEFAULT_BLOCKED_COMMANDS,
                "may_use_skills": [],
                "validation_required": ["Run targeted validation when available"],
                "unblocks": "reviewer phase",
                "status": "pending",
            }
            tasks.append(worker)
            index += 1

    for focus in args.reviewers:
        reviewer = {
            "task_id": task_id(index),
            "session_name": f"reviewer-{focus}",
            "runtime": args.runtime,
            "mode": "review",
            "role": "Reviewer",
            "title": f"Review {focus}",
            "objective": f"Review {args.task} with focus on {focus}",
            "allowed_paths": ["**/*"],
            "blocked_paths": DEFAULT_BLOCKED_PATHS,
            "allowed_commands": ["rg", "git diff", "git status"],
            "blocked_commands": DEFAULT_BLOCKED_COMMANDS,
            "may_use_skills": [args.review_skill] if args.review_skill else [],
            "validation_required": ["Return findings by severity"],
            "unblocks": "verifier",
            "status": "pending",
        }
        tasks.append(reviewer)
        index += 1

    if args.mode in {"implement", "refactor", "fix", "review"}:
        verifier = {
            "task_id": task_id(index),
            "session_name": "verifier",
            "runtime": args.runtime,
            "mode": "verify",
            "role": "Verifier",
            "title": "Verify end-to-end",
            "objective": f"Run validation and confirm {args.task} is ready for Main audit and delivery",
            "allowed_paths": ["**/*"],
            "blocked_paths": DEFAULT_BLOCKED_PATHS,
            "allowed_commands": ["npm test", "pnpm test", "pytest", "git diff", "git status"],
            "blocked_commands": DEFAULT_BLOCKED_COMMANDS,
            "may_use_skills": [],
            "validation_required": ["Record validation commands and outcomes"],
            "unblocks": "scope_audit and final_delivery",
            "status": "pending",
        }
        tasks.append(verifier)

    for task in tasks:
        task["required_paths"] = required_paths_for_task(task, tasks)

    return tasks, warnings


def write_status_json(state_dir: Path, task_title: str, tasks: list[dict], workspace_root: Path) -> Path:
    gates = {
        "explorers_complete": {
            "status": "pending",
            "required_task_ids": [t["task_id"] for t in tasks if t["role"] == "Explorer"],
            "completed_task_ids": [],
        },
        "workers_complete": {
            "status": "pending",
            "required_task_ids": [t["task_id"] for t in tasks if t["role"] == "Worker"],
            "completed_task_ids": [],
        },
        "review_complete": {
            "status": "pending",
            "required_task_ids": [t["task_id"] for t in tasks if t["role"] == "Reviewer"],
            "completed_task_ids": [],
        },
        "verify_complete": {
            "status": "pending",
            "required_task_ids": [t["task_id"] for t in tasks if t["role"] == "Verifier"],
            "completed_task_ids": [],
        },
        "scope_audit": {
            "status": "pending",
            "required_task_ids": [],
            "completed_task_ids": [],
            "note": "Run audit_worker_output.py --write-audit after Workers finish",
        },
        "final_delivery": {
            "status": "pending",
            "required_task_ids": [],
            "completed_task_ids": [],
            "note": "Main delivers after all upstream gates pass",
        },
    }
    status_doc = {
        "schema_version": 1,
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "task_title": task_title,
        "state_dir": str(state_dir),
        "workspace_root": str(workspace_root),
        "target_repo": str(workspace_root),
        "generated_at": utc_now(),
        "updated_at": utc_now(),
        "current_phase": "explorers_complete",
        "gates": gates,
        "tasks": {
            task["task_id"]: {
                "task_id": task["task_id"],
                "session_name": task["session_name"],
                "role": task["role"],
                "status": "pending",
                "updated_at": utc_now(),
            }
            for task in tasks
        },
    }
    status_path = state_dir / "status.json"
    status_path.write_text(json.dumps(status_doc, indent=2) + "\n", encoding="utf-8")
    return status_path


def write_run_plan(state_dir: Path, tasks: list[dict]) -> Path:
    phases = []
    for role in ROLE_ORDER:
        role_tasks = [task for task in tasks if task["role"] == role]
        if not role_tasks:
            continue
        phases.append(
            {
                "phase": GATE_BY_ROLE[role],
                "role": role,
                "task_ids": [task["task_id"] for task in role_tasks],
                "main_gate_command": f"python adapters/openclaw/scripts/update_task_status.py --state-dir {state_dir} --sync",
            }
        )
    phases.extend(
        [
            {
                "phase": "scope_audit",
                "role": "Main",
                "main_gate_command": (
                    f"python adapters/openclaw/scripts/audit_worker_output.py "
                    f"--ownership {state_dir}/ownership.json "
                    f"--results {state_dir}/results "
                    f"--changed-files {state_dir}/changed-files.txt "
                    f"--write-audit --state-dir {state_dir}"
                ),
            },
            {
                "phase": "final_delivery",
                "role": "Main",
                "main_gate_command": (
                    f"python adapters/openclaw/scripts/update_task_status.py "
                    f"--state-dir {state_dir} --summarize"
                ),
            },
        ]
    )
    plan = {
        "schema_version": 1,
        "workflow": "Explorer -> Worker -> Reviewer -> Verifier -> Main audit -> final delivery",
        "phases": phases,
    }
    plan_path = state_dir / "run-plan.json"
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan_path


def write_outputs(
    tasks: list[dict],
    state_dir: Path,
    task_title: str,
    runtime: str,
    workspace_root: Path,
) -> dict:
    out_dir = state_dir / "tasks"
    results_dir = state_dir / "results"
    findings_dir = state_dir / "findings"
    approvals_dir = state_dir / "approvals"
    audits_dir = state_dir / "audits"
    summary_dir = state_dir / "summary"

    for directory in (out_dir, results_dir, findings_dir, approvals_dir, audits_dir, summary_dir):
        directory.mkdir(parents=True, exist_ok=True)

    for task in tasks:
        task.setdefault("target_repo", str(workspace_root))
        write_card(out_dir / f"{task['task_id']}-{task['session_name']}.md", task, state_dir, tasks, workspace_root)

    ownership = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "task": task_title,
        "state_dir": str(state_dir),
        "workspace_root": str(workspace_root),
        "target_repo": str(workspace_root),
        "adapter_root": str(ADAPTER_ROOT),
        "adapter_scripts": {
            "create_task_cards": adapter_script("create_task_cards.py"),
            "update_task_status": adapter_script("update_task_status.py"),
            "audit_worker_output": adapter_script("audit_worker_output.py"),
            "verify_workspace": adapter_script("verify_workspace.py"),
        },
        "tasks": [],
    }
    for item in tasks:
        paths = result_paths(state_dir, item)
        constraints = ROLE_CONSTRAINTS.get(item["role"], ROLE_CONSTRAINTS["Worker"])
        ownership["tasks"].append(
            {
                "task_id": item["task_id"],
                "session_name": item["session_name"],
                "role": item["role"],
                "mode": item["mode"],
                "runtime": runtime,
                "write_permission": constraints["write_permission"],
                "allowed_paths": item["allowed_paths"],
                "required_paths": item.get("required_paths") or required_paths_for_task(item, tasks),
                "blocked_paths": item["blocked_paths"],
                # Persist the static dependency graph so sync can surface
                # ready_to_spawn / blocked_by at runtime (auto-unblock).
                "dependencies": prerequisite_ids(tasks, item),
                "result_report_json": paths["json"],
                "result_report_markdown": paths["markdown"],
                "tools_used": tools_for_task(item),
                "status": item["status"],
            }
        )

    ownership_path = state_dir / "ownership.json"
    ownership_path.write_text(json.dumps(ownership, indent=2) + "\n", encoding="utf-8")
    status_path = write_status_json(state_dir, task_title, tasks, workspace_root)
    plan_path = write_run_plan(state_dir, tasks)

    return {
        "tasks": len(tasks),
        "out": str(out_dir),
        "ownership": str(ownership_path),
        "results": str(results_dir),
        "status": str(status_path),
        "run_plan": str(plan_path),
        "findings": str(findings_dir),
        "approvals": str(approvals_dir),
        "audits": str(audits_dir),
    }


def run_self_check() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="openclaw-task-cards-") as tmp:
        state_dir = Path(tmp) / ".codex-multi-agent"
        args = argparse.Namespace(
            task="Self-check favorite feature",
            mode="implement",
            modules=["backend", "frontend"],
            runtime="acp",
            reviewers=["correctness"],
            review_skill="ssrd",
        )
        tasks, _warnings = build_tasks(args)
        workspace_root = REPO_ROOT.resolve()
        summary = write_outputs(tasks, state_dir, args.task, args.runtime, workspace_root)
        ownership = json.loads((state_dir / "ownership.json").read_text(encoding="utf-8"))
        if ownership.get("schema_version") != 1:
            errors.append("ownership.json missing schema_version")
        workers = [t for t in ownership["tasks"] if t["role"] == "Worker"]
        verifiers = [t for t in ownership["tasks"] if t["role"] == "Verifier"]
        if not workers:
            errors.append("expected at least one Worker in self-check output")
        if not verifiers:
            errors.append("expected Verifier task in self-check output")
        explorer_ids = {t["task_id"] for t in ownership["tasks"] if t["role"] == "Explorer"}
        for worker in workers:
            for key in ("result_report_json", "result_report_markdown", "allowed_paths", "required_paths", "dependencies"):
                if key not in worker:
                    errors.append(f"Worker {worker['task_id']} missing {key}")
            # Worker should declare a dependency on its module Explorer (persisted graph).
            if not any(dep in explorer_ids for dep in worker.get("dependencies", [])):
                errors.append(f"Worker {worker['task_id']} should depend on an Explorer in ownership.dependencies")
        card_path = state_dir / "tasks" / f"{workers[0]['task_id']}-{workers[0]['session_name']}.md"
        card_text = card_path.read_text(encoding="utf-8")
        verify_script = adapter_script("verify_workspace.py")
        if verify_script not in card_text:
            errors.append("task card preflight must use absolute verify_workspace.py path")

        for needle in (
            "workspace_root:",
            "target_repo:",
            "preflight_command:",
            "execution_guidance:",
            "required_paths:",
            "Preflight (required first step)",
            "required_paths_verified=true",
            "result_report_paths:",
            "openclaw_handoff:",
            "gate:",
            "main_commands:",
        ):
            if needle not in card_text:
                errors.append(f"task card missing {needle}")

        adapter_args = argparse.Namespace(
            task="Dogfood openclaw adapter",
            mode="review",
            modules=["openclaw_adapter"],
            runtime="subagent",
            reviewers=["correctness"],
            review_skill="ssrd",
        )
        adapter_tasks, _ = build_tasks(adapter_args)
        explorer = next(t for t in adapter_tasks if t.get("module") == "openclaw_adapter" and t["role"] == "Explorer")
        if explorer["allowed_paths"] != ["adapters/openclaw/**"]:
            errors.append(f"openclaw_adapter should map to adapters/openclaw/**, got {explorer['allowed_paths']}")
        reviewer = next(t for t in adapter_tasks if t["role"] == "Reviewer")
        if "adapters/openclaw/**" not in reviewer.get("required_paths", []):
            errors.append("reviewer should inherit module required_paths when allowed_paths is **/*")

        if not (state_dir / "status.json").exists():
            errors.append("status.json not created")
        if not (state_dir / "run-plan.json").exists():
            errors.append("run-plan.json not created")
        if ownership.get("workspace_root") != str(workspace_root):
            errors.append("ownership.json missing workspace_root")

        verify_script = SCRIPT_DIR / "verify_workspace.py"
        import subprocess

        proc = subprocess.run(
            [
                sys.executable,
                str(verify_script),
                "--workspace-root",
                str(workspace_root),
                "--required-paths",
                adapter_required_path(),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            errors.append(f"verify_workspace self-check failed: {proc.stderr or proc.stdout}")

        audit_script = SCRIPT_DIR / "audit_worker_output.py"
        for worker in workers:
            allowed_paths = worker.get("allowed_paths", [])
            first_allowed = allowed_paths[0] if allowed_paths else f"{worker.get('module', 'module')}/**"
            base_path = first_allowed.replace("/**", "").rstrip("/") or "."
            sample_file = f"{base_path}/{worker['session_name']}.py" if base_path != "." else f"{worker['session_name']}.py"
            sample_result = {
                "task_id": worker["task_id"],
                "session_name": worker["session_name"],
                "role": "Worker",
                "status": "completed",
                "files_changed": [sample_file],
            }
            result_path = Path(worker["result_report_json"])
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(json.dumps(sample_result, indent=2), encoding="utf-8")

        proc = subprocess.run(
            [
                sys.executable,
                str(audit_script),
                "--ownership",
                summary["ownership"],
                "--results",
                summary["results"],
                "--write-audit",
                "--state-dir",
                str(state_dir),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            errors.append(f"audit self-check failed: {proc.stderr or proc.stdout}")
        if not list((state_dir / "audits").glob("audit-*.json")):
            errors.append("audit JSON not written during self-check")

        mc_state_dir = str(state_dir)
        mc_worker = workers[0]
        mc_result = {
            "task_id": mc_worker["task_id"],
            "role": "Worker",
            "status": "completed",
            "files_changed": [
                f".codex-multi-agent/results/{mc_worker['task_id']}-{mc_worker['session_name']}.json",
                "backend/sample.py",
            ],
        }
        mc_result_path = Path(mc_worker["result_report_json"])
        mc_result_path.write_text(json.dumps(mc_result, indent=2), encoding="utf-8")
        ownership_mc = json.loads((state_dir / "ownership.json").read_text(encoding="utf-8"))
        ownership_mc["state_dir"] = mc_state_dir
        (state_dir / "ownership.json").write_text(json.dumps(ownership_mc, indent=2) + "\n", encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(audit_script),
                "--ownership",
                summary["ownership"],
                "--results",
                summary["results"],
                "--write-audit",
                "--state-dir",
                str(state_dir),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            errors.append(f"mission-control files_changed audit failed: {proc.stderr or proc.stdout}")
        mc_audit = json.loads((state_dir / "audits" / "latest.json").read_text(encoding="utf-8"))
        if any(v.get("reason") == "Outside allowed_paths" for v in mc_audit.get("violations", [])):
            errors.append("Worker listing mission-control result paths must not trigger Outside allowed_paths")

        verifier_card = next(
            (state_dir / "tasks" / f"{t['task_id']}-{t['session_name']}.md").read_text(encoding="utf-8")
            for t in tasks
            if t["role"] == "Verifier"
        )
        for needle in ("files_read", "pytest", "test pass alone"):
            if needle not in verifier_card:
                errors.append(f"Verifier task card missing guidance: {needle}")

        status_script = SCRIPT_DIR / "update_task_status.py"
        proc = subprocess.run(
            [sys.executable, str(status_script), "--self-check"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode != 0:
            errors.append(f"update_task_status self-check failed: {proc.stderr or proc.stdout}")

        fizz_args = argparse.Namespace(
            task="FizzBuzz module paths",
            mode="implement",
            module_specs=[{"name": "fizzbuzz", "paths": ["src/**", "tests/**"]}],
            modules=[],
            runtime="acp",
            reviewers=[],
            review_skill="ssrd",
        )
        fizz_tasks, fizz_warnings = build_tasks(fizz_args)
        fizz_worker = next(t for t in fizz_tasks if t.get("module") == "fizzbuzz" and t["role"] == "Worker")
        if fizz_worker.get("allowed_paths") != ["src/**", "tests/**"]:
            errors.append(f"fizzbuzz explicit paths expected src/** and tests/**, got {fizz_worker.get('allowed_paths')}")
        if fizz_warnings:
            errors.append(f"explicit module paths should not emit warnings, got {fizz_warnings}")

        unknown_args = argparse.Namespace(
            task="Unknown module default paths",
            mode="implement",
            module_specs=[{"name": "fizzbuzz", "paths": None}],
            modules=[],
            runtime="acp",
            reviewers=[],
            review_skill="ssrd",
        )
        _unknown_tasks, unknown_warnings = build_tasks(unknown_args)
        if not unknown_warnings or "fizzbuzz" not in unknown_warnings[0]:
            errors.append("unknown module without explicit paths should emit path warning")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "create_task_cards self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="Run built-in validation and exit")
    parser.add_argument("--task", help="High-level user task")
    parser.add_argument("--from-yaml", help="Load task/mode/modules/reviewers from a simple YAML file")
    parser.add_argument(
        "--from-json",
        help="Load task/mode/modules (with optional per-module paths) from JSON with the same shape as YAML",
    )
    parser.add_argument("--mode", default="implement", choices=["research", "implement", "fix", "review", "refactor"])
    parser.add_argument("--modules", nargs="+", default=["backend", "frontend", "tests"], help="Module names")
    parser.add_argument("--out", default=".codex-multi-agent", help="Coordination state directory")
    parser.add_argument("--runtime", default="acp", choices=list(TASK_CARD_RUNTIME_CHOICES))
    parser.add_argument("--reviewers", nargs="*", default=["correctness", "security"], help="Reviewer focus areas")
    parser.add_argument("--review-skill", default="ssrd", help="Review skill to authorize for reviewers")
    parser.add_argument(
        "--workspace-root",
        help="Absolute path to target repo (default: current working directory, resolved)",
    )
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    config_data: dict | None = None
    if args.from_json:
        config_data = json.loads(Path(args.from_json).read_text(encoding="utf-8-sig"))
    elif args.from_yaml:
        yaml_text = Path(args.from_yaml).read_text(encoding="utf-8-sig")
        nested_modules = parse_modules_yaml_section(yaml_text)
        yaml_data = parse_simple_yaml(yaml_text)
        if nested_modules:
            yaml_data["modules"] = nested_modules
        config_data = yaml_data

    if config_data:
        args.task = args.task or config_data.get("task")
        args.mode = config_data.get("mode", args.mode)
        if "modules" in config_data:
            args.module_specs = normalize_module_specs(config_data["modules"])
            args.modules = [spec["name"] for spec in args.module_specs]
        if "reviewers" in config_data:
            args.reviewers = config_data["reviewers"]
        if config_data.get("runtime"):
            args.runtime = config_data["runtime"]
        if config_data.get("review_skill"):
            args.review_skill = config_data["review_skill"]
        reviewer_skills = config_data.get("skills", {})
        if isinstance(reviewer_skills, dict) and reviewer_skills.get("reviewer"):
            args.review_skill = reviewer_skills["reviewer"][0]

    if not args.task:
        parser.error("--task is required unless --self-check, --from-yaml, or --from-json is used")

    state_dir = Path(args.out)
    workspace_root = resolve_workspace_root(args.workspace_root)
    tasks, path_warnings = build_tasks(args)
    summary = write_outputs(tasks, state_dir, args.task, args.runtime, workspace_root)
    output = {"ok": True, "workspace_root": str(workspace_root), **summary}
    if path_warnings:
        output["warnings"] = path_warnings
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
