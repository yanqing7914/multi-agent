#!/usr/bin/env python3
"""Audit OpenClaw Worker outputs against ownership rules."""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from _preflight import (
    changed_files_metadata,
    false_completion_reason,
    thin_evidence_reason,
    workspace_mismatch_reason,
)

SECRET_PATTERNS = [
    ".env",
    ".env.*",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_ed25519",
    "**/credentials.json",
    "**/secrets/**",
]


def normalize(path: str) -> str:
    path = path.replace("\\", "/").strip()
    while path.startswith("./"):
        path = path[2:]
    return path


def mission_control_exempt(path: str, state_dir: str | None) -> bool:
    """Paths under mission-control state dirs must not count toward Worker ownership."""
    path = normalize(path)
    first = path.split("/")[0] if path else ""
    if first.startswith(".codex-multi-agent"):
        return True
    if state_dir:
        state_norm = normalize(str(state_dir)).rstrip("/")
        if path == state_norm or path.startswith(state_norm + "/"):
            return True
    return False


def _segment_glob_match(path: str, pattern: str) -> bool:
    if pattern == "**":
        return True
    if pattern.endswith("/**"):
        base = pattern[:-3]
        return path == base or path.startswith(base + "/")
    if pattern.startswith("**/"):
        suffix = pattern[3:]
        if fnmatch.fnmatch(path, suffix):
            return True
        for index in range(path.count("/") + 1):
            candidate = "/".join(path.split("/")[index:])
            if fnmatch.fnmatch(candidate, suffix):
                return True
        return False
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path.split("/")[-1], pattern)


def matches(path: str, patterns: list[str]) -> bool:
    path = normalize(path)
    for pattern in patterns:
        pattern = normalize(pattern)
        if pattern.startswith("~/"):
            continue
        if _segment_glob_match(path, pattern):
            return True
    return False


def workspace_relative(path: str, workspace_root: str | None) -> str:
    normalized = normalize(path)
    if not workspace_root:
        return normalized
    try:
        candidate = Path(normalized)
        if not candidate.is_absolute():
            return normalized
        rel = candidate.resolve().relative_to(Path(workspace_root).resolve())
        return normalize(str(rel))
    except (OSError, ValueError):
        return normalized


def load_changed_files(path: Path | None) -> list[str]:
    if not path or not path.exists():
        return []
    return [normalize(line.strip()) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def parse_markdown_result(text: str) -> dict:
    data: dict = {"files_changed": []}
    scalar_fields = {
        "task_id",
        "session_name",
        "role",
        "status",
        "summary",
        "handoff_notes",
        "workspace_observed",
        "required_paths_verified",
    }
    list_fields = {
        "files_read",
        "tools_used",
        "files_changed",
        "skills_used",
        "commands_run",
        "findings",
        "risks",
        "blockers",
        "required_paths_checked",
        "required_paths_missing",
    }
    current_list: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if re.match(r"^\s+- ", line) and current_list in list_fields:
            data.setdefault(current_list, []).append(normalize(line.strip()[2:].strip().strip('"')))
            continue
        current_list = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in scalar_fields:
            data[key] = value.strip('"').strip("'")
            continue
        if key in list_fields and not value:
            current_list = key
            data.setdefault(key, [])
    return data


def load_result_file(path: Path) -> dict | None:
    if path.suffix.lower() == ".json":
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            return None
    if path.suffix.lower() == ".md":
        return parse_markdown_result(path.read_text(encoding="utf-8-sig"))
    return None


def infer_task_id(path: Path, data: dict) -> str | None:
    if data.get("task_id"):
        return str(data["task_id"])
    match = re.match(r"^(T\d+)-", path.stem)
    if match:
        return match.group(1)
    return None


def load_result_changes(results_dir: Path | None) -> dict[str, dict]:
    changes: dict[str, dict] = {}
    if not results_dir or not results_dir.exists():
        return changes
    for result_file in sorted(results_dir.iterdir()):
        if result_file.suffix.lower() not in {".json", ".md"}:
            continue
        data = load_result_file(result_file)
        if not data:
            continue
        task_id = infer_task_id(result_file, data)
        if not task_id:
            continue
        files = [normalize(item) for item in data.get("files_changed", []) if str(item).strip()]
        entry = changes.setdefault(
            task_id,
            {
                "files": [],
                "role": data.get("role"),
                "status": data.get("status"),
                "source_files": [],
            },
        )
        entry["files"].extend(files)
        entry["source_files"].append(str(result_file))
        if data.get("role"):
            entry["role"] = data.get("role")
        if data.get("status"):
            entry["status"] = data.get("status")
    return changes


def parse_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return None


def normalize_tool_name(name: str) -> str:
    name = name.strip().lower()
    if name.endswith(".py"):
        name = name[:-3]
    return name


def tools_used_warnings(task: dict, merged: dict) -> list[dict]:
    """Warn when result report references tools not declared on the task card."""
    declared = {normalize_tool_name(item) for item in task.get("tools_used") or []}
    reported_raw = merged.get("tools_used") or []
    if not isinstance(reported_raw, list):
        reported_raw = [reported_raw]
    warnings: list[dict] = []
    if not reported_raw:
        warnings.append(
            {
                "task_id": task.get("task_id"),
                "reason": "missing_tools_used",
                "detail": "Result report has empty tools_used (warning only; backward compatible)",
            }
        )
        return warnings
    for item in reported_raw:
        tool = normalize_tool_name(str(item))
        if not tool:
            continue
        if declared and tool not in declared and not any(tool in d for d in declared):
            warnings.append(
                {
                    "task_id": task.get("task_id"),
                    "reason": "undeclared_tool_used",
                    "tool": tool,
                    "declared_tools_used": sorted(declared),
                }
            )
    return warnings


def audit(ownership: dict, result_changes: dict[str, dict], global_changed: list[str], strict: bool) -> dict:
    tasks = ownership.get("tasks", [])
    task_by_id = {task["task_id"]: task for task in tasks}
    workers = [task for task in tasks if task.get("role") == "Worker"]
    expected_workspace = ownership.get("workspace_root") or ownership.get("target_repo")
    state_dir = ownership.get("state_dir")

    violations: list[dict] = []
    warnings: list[dict] = []
    touched_by_path: dict[str, list[str]] = {}

    for task_id, result in result_changes.items():
        files = list(dict.fromkeys(workspace_relative(item, expected_workspace) for item in result["files"]))
        task = task_by_id.get(task_id)
        if not task:
            warnings.append({"task_id": task_id, "reason": "Result has no matching ownership task"})
            continue

        source_files = result.get("source_files", [])
        false_reason = None
        thin_reason = None
        mismatch_reason = None
        required_paths = task.get("required_paths") or []
        # Merge fields across JSON + Markdown source files; JSON values win when present.
        merged: dict = {}
        sorted_sources = sorted(source_files, key=lambda x: 0 if str(x).lower().endswith('.json') else 1)
        for source in sorted_sources:
            loaded = load_result_file(Path(source))
            if not loaded:
                continue
            for k, v in loaded.items():
                if k not in merged or merged.get(k) in (None, [], '', False):
                    merged[k] = v
        if merged:
            mismatch_reason = workspace_mismatch_reason(merged, expected_workspace)
            if not mismatch_reason:
                false_reason = false_completion_reason(merged)
            if not mismatch_reason and not false_reason:
                thin_reason = thin_evidence_reason(merged, required_paths)
        if mismatch_reason:
            violations.append(
                {
                    "task_id": task_id,
                    "reason": "Workspace mismatch blocked: workspace_observed does not match target repo",
                    "detail": mismatch_reason,
                }
            )
            continue
        if false_reason:
            violations.append(
                {
                    "task_id": task_id,
                    "reason": "False completion blocked: reported completed but required paths were not verified",
                    "detail": false_reason,
                }
            )
            continue
        if thin_reason:
            violations.append(
                {
                    "task_id": task_id,
                    "reason": "Thin evidence blocked: claimed verification without files_read",
                    "detail": thin_reason,
                }
            )
            continue

        warnings.extend(tools_used_warnings(task, merged))

        reported_role = result.get("role") or task.get("role")
        if reported_role and reported_role != task.get("role"):
            violations.append(
                {
                    "task_id": task_id,
                    "reason": "Result role does not match ownership role",
                    "expected": task.get("role"),
                    "actual": reported_role,
                }
            )

        if task.get("role") != "Worker":
            if files:
                violations.append(
                    {
                        "task_id": task_id,
                        "reason": "Non-Worker reported changed files",
                        "role": task.get("role"),
                        "files": files,
                    }
                )
            continue

        allowed = task.get("allowed_paths", [])
        blocked = list(dict.fromkeys(task.get("blocked_paths", []) + SECRET_PATTERNS))
        for file_path in files:
            if mission_control_exempt(file_path, state_dir):
                continue
            touched_by_path.setdefault(file_path, []).append(task_id)
            if matches(file_path, blocked):
                violations.append({"task_id": task_id, "path": file_path, "reason": "Matches blocked/secret path"})
            elif not matches(file_path, allowed):
                violations.append({"task_id": task_id, "path": file_path, "reason": "Outside allowed_paths"})

    if global_changed:
        global_changed = list(dict.fromkeys(workspace_relative(item, expected_workspace) for item in global_changed))
        for file_path in global_changed:
            blocked_union = SECRET_PATTERNS + [
                pattern
                for task in tasks
                for pattern in task.get("blocked_paths", [])
            ]
            if matches(file_path, blocked_union):
                violations.append({"path": file_path, "reason": "Changed file matches blocked/secret path"})
            owners = [task["task_id"] for task in workers if matches(file_path, task.get("allowed_paths", []))]
            if not owners:
                item = {"path": file_path, "reason": "Changed file is not owned by any Worker"}
                if strict:
                    violations.append(item)
                else:
                    warnings.append(item)
            elif len(owners) > 1:
                item = {
                    "path": file_path,
                    "reason": "Changed file matches multiple Worker ownership scopes",
                    "tasks": owners,
                }
                if strict:
                    violations.append(item)
                else:
                    warnings.append(item)

    conflicts = [
        {"path": path, "tasks": ids, "reason": "Multiple Workers reported same changed file"}
        for path, ids in touched_by_path.items()
        if len(set(ids)) > 1
    ]

    for task in workers:
        task_id = task["task_id"]
        if task_id not in result_changes:
            item = {"task_id": task_id, "reason": "Worker result report not found"}
            if strict:
                violations.append(item)
            else:
                warnings.append(item)
            continue
        if result_changes[task_id]["status"] == "blocked":
            warnings.append({"task_id": task_id, "reason": "Worker reported blocked status"})

    gate_warnings = [item for item in warnings if item.get("reason") != "missing_tools_used"]
    if violations or conflicts:
        audit_gate_status = "failed"
    elif gate_warnings:
        audit_gate_status = "pending"
    else:
        audit_gate_status = "passed"
    # ok means scope_audit gate passed — never true when gate is pending or failed
    ok = audit_gate_status == "passed"
    return {
        "ok": ok,
        "violations": violations,
        "conflicts": conflicts,
        "warnings": warnings,
        "summary": {
            "workers": len(workers),
            "results_found": len(result_changes),
            "global_changed_files": len(global_changed),
        },
        "main_next_steps": main_next_steps(audit_gate_status, violations, conflicts, warnings, strict),
        "gate": {
            "id": "scope_audit",
            "status": audit_gate_status,
            "blocks": "final_delivery" if audit_gate_status != "passed" else None,
        },
    }


def main_next_steps(
    gate_status: str,
    violations: list[dict],
    conflicts: list[dict],
    warnings: list[dict],
    strict: bool,
) -> list[str]:
    if gate_status == "passed":
        return [
            "Scope audit passed. Main may proceed to Reviewer/Verifier gates or final delivery.",
            "Run: python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync",
        ]
    if gate_status == "pending":
        steps = ["Scope audit incomplete. Waiting on Worker reports or changed-file capture."]
        if warnings:
            steps.append(f"Address {len(warnings)} warning(s) — missing reports or unowned paths.")
        steps.append(
            "Capture: git diff --name-only > .codex-multi-agent/changed-files.txt "
            "then rerun audit_worker_output.py --write-audit"
        )
        return steps
    steps = ["Scope audit failed. Main must triage before final delivery."]
    if violations:
        steps.append(f"Resolve {len(violations)} violation(s) — check paths and Worker reports.")
    if conflicts:
        steps.append(f"Resolve {len(conflicts)} Worker conflict(s) — split ownership or re-run Workers.")
    if warnings and not strict:
        steps.append(f"Review {len(warnings)} warning(s); rerun with --strict to fail on warnings.")
    steps.append(
        "After fixes: git diff --name-only > .codex-multi-agent/changed-files.txt "
        "and rerun audit_worker_output.py --write-audit"
    )
    return steps


def write_audit_report(
    report: dict,
    state_dir: Path,
    changed_files_path: Path | None = None,
) -> Path:
    audits_dir = state_dir / "audits"
    audits_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit_path = audits_dir / f"audit-{stamp}.json"
    inputs = changed_files_metadata(changed_files_path or (state_dir / "changed-files.txt"))
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **inputs,
        **report,
    }
    audit_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    latest_path = audits_dir / "latest.json"
    latest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return audit_path


def run_self_check() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="openclaw-audit-") as tmp:
        root = Path(tmp)
        ownership = {
            "schema_version": 1,
            "tasks": [
                {
                    "task_id": "T001",
                    "session_name": "worker-backend",
                    "role": "Worker",
                    "allowed_paths": ["backend/**"],
                    "blocked_paths": [".env"],
                    "status": "pending",
                },
                {
                    "task_id": "T002",
                    "session_name": "worker-frontend",
                    "role": "Worker",
                    "allowed_paths": ["frontend/**"],
                    "blocked_paths": [".env"],
                    "status": "pending",
                },
                {
                    "task_id": "T003",
                    "session_name": "reviewer-security",
                    "role": "Reviewer",
                    "allowed_paths": ["**/*"],
                    "blocked_paths": [".env"],
                    "status": "pending",
                },
            ],
        }
        ownership_path = root / "ownership.json"
        ownership_path.write_text(json.dumps(ownership, indent=2), encoding="utf-8")
        results_dir = root / "results"
        results_dir.mkdir()
        (results_dir / "T001-worker-backend.json").write_text(
            json.dumps(
                {
                    "task_id": "T001",
                    "role": "Worker",
                    "status": "completed",
                    "files_changed": ["backend/src/app.py"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (results_dir / "T003-reviewer-security.md").write_text(
            "\n".join(
                [
                    "task_id: T003",
                    "session_name: reviewer-security",
                    "role: Reviewer",
                    "status: completed",
                    "files_changed: []",
                    "findings:",
                    "  - severity: low",
                ]
            ),
            encoding="utf-8",
        )

        (results_dir / "T002-worker-frontend.json").write_text(
            json.dumps(
                {
                    "task_id": "T002",
                    "role": "Worker",
                    "status": "completed",
                    "files_changed": ["frontend/src/app.tsx"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        good = audit(ownership, load_result_changes(results_dir), [], strict=False)
        if not good["ok"] or good["gate"]["status"] != "passed":
            errors.append(f"expected clean audit with gate passed, got {good}")

        bad_results = results_dir / "T002-worker-frontend.json"
        bad_results.write_text(
            json.dumps(
                {
                    "task_id": "T002",
                    "role": "Worker",
                    "status": "completed",
                    "files_changed": ["backend/src/leak.py", ".env"],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        bad = audit(ownership, load_result_changes(results_dir), ["README.md"], strict=False)
        if bad["ok"]:
            errors.append("expected failing audit for out-of-scope and secret paths")
        expected_reasons = {item["reason"] for item in bad["violations"] + bad["warnings"]}
        for reason in (
            "Outside allowed_paths",
            "Matches blocked/secret path",
            "Changed file is not owned by any Worker",
        ):
            if reason not in expected_reasons:
                errors.append(f"missing expected finding: {reason}")

        only_t001 = results_dir / "only-t001"
        only_t001.mkdir(exist_ok=True)
        (only_t001 / "T001-worker-backend.json").write_text(
            (results_dir / "T001-worker-backend.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        missing_report = audit(ownership, load_result_changes(only_t001), [], strict=False)
        if not any(item["reason"] == "Worker result report not found" for item in missing_report["warnings"]):
            errors.append("expected missing Worker report warning")
        if missing_report["ok"]:
            errors.append("audit with warnings must set ok=false")
        if missing_report["gate"]["status"] != "pending":
            errors.append("audit with warnings must set gate.status=pending")

        overlap = {
            "schema_version": 1,
            "tasks": [
                {
                    "task_id": "T001",
                    "session_name": "worker-a",
                    "role": "Worker",
                    "allowed_paths": ["shared/**"],
                    "blocked_paths": [],
                    "status": "pending",
                },
                {
                    "task_id": "T002",
                    "session_name": "worker-b",
                    "role": "Worker",
                    "allowed_paths": ["shared/**"],
                    "blocked_paths": [],
                    "status": "pending",
                },
            ],
        }
        overlap_results = {
            "T001": {"files": ["shared/x.py"], "role": "Worker", "status": "completed", "source_files": []},
            "T002": {"files": ["shared/x.py"], "role": "Worker", "status": "completed", "source_files": []},
        }
        overlap_report = audit(overlap, overlap_results, ["shared/x.py"], strict=True)
        if not overlap_report["conflicts"]:
            errors.append("expected Worker overlap conflict")

        false_completion = {
            "task_id": "T004",
            "role": "Reviewer",
            "status": "completed",
            "required_paths_verified": False,
            "required_paths_missing": ["adapters/openclaw/**"],
            "files_changed": [],
        }
        false_results = root / "false-results"
        false_results.mkdir()
        (false_results / "T004-reviewer-false-complete.json").write_text(
            json.dumps(false_completion, indent=2),
            encoding="utf-8",
        )
        false_ownership = {
            "schema_version": 1,
            "tasks": [
                {
                    "task_id": "T004",
                    "session_name": "reviewer-false-complete",
                    "role": "Reviewer",
                    "allowed_paths": ["**/*"],
                    "required_paths": ["adapters/openclaw/**"],
                    "blocked_paths": [".env"],
                    "status": "pending",
                }
            ],
        }
        false_report = audit(false_ownership, load_result_changes(false_results), [], strict=False)
        if false_report["ok"]:
            errors.append("expected audit failure for false completion with missing required paths")
        if not any("False completion blocked" in item.get("reason", "") for item in false_report["violations"]):
            errors.append("expected false completion violation in audit report")

        thin_completion = {
            "task_id": "T005",
            "role": "Reviewer",
            "status": "completed",
            "required_paths_verified": True,
            "required_paths_missing": [],
            "files_read": [],
            "files_changed": [],
        }
        thin_results = root / "thin-results"
        thin_results.mkdir()
        (thin_results / "T005-reviewer-thin.json").write_text(
            json.dumps(thin_completion, indent=2),
            encoding="utf-8",
        )
        thin_ownership = {
            "schema_version": 1,
            "tasks": [
                {
                    "task_id": "T005",
                    "session_name": "reviewer-thin",
                    "role": "Reviewer",
                    "allowed_paths": ["**/*"],
                    "required_paths": ["adapters/openclaw/**"],
                    "blocked_paths": [".env"],
                    "status": "pending",
                }
            ],
        }
        thin_report = audit(thin_ownership, load_result_changes(thin_results), [], strict=False)
        if thin_report["ok"]:
            errors.append("expected audit failure for thin evidence (empty files_read)")
        if not any("Thin evidence" in item.get("reason", "") for item in thin_report["violations"]):
            errors.append("expected thin evidence violation in audit report")

        mismatch_completion = {
            "task_id": "T006",
            "role": "Reviewer",
            "status": "completed",
            "workspace_observed": "/tmp/wrong",
            "required_paths_verified": True,
            "files_read": ["adapters/openclaw/SKILL.md"],
            "files_changed": [],
        }
        mismatch_results = root / "mismatch-results"
        mismatch_results.mkdir()
        (mismatch_results / "T006-reviewer-mismatch.json").write_text(
            json.dumps(mismatch_completion, indent=2),
            encoding="utf-8",
        )
        mismatch_ownership = {
            "schema_version": 1,
            "workspace_root": str(root / "expected-repo"),
            "tasks": [
                {
                    "task_id": "T006",
                    "session_name": "reviewer-mismatch",
                    "role": "Reviewer",
                    "allowed_paths": ["**/*"],
                    "required_paths": ["adapters/openclaw/**"],
                    "blocked_paths": [".env"],
                    "status": "pending",
                }
            ],
        }
        mismatch_report = audit(mismatch_ownership, load_result_changes(mismatch_results), [], strict=False)
        if mismatch_report["ok"]:
            errors.append("expected audit failure for workspace_observed mismatch")
        if not any("Workspace mismatch" in item.get("reason", "") for item in mismatch_report["violations"]):
            errors.append("expected workspace mismatch violation in audit report")

        mc_state = str(root / ".codex-multi-agent-real-fix")
        mc_ownership = {
            "schema_version": 1,
            "state_dir": mc_state,
            "tasks": [
                {
                    "task_id": "T010",
                    "session_name": "worker-fizzbuzz",
                    "role": "Worker",
                    "allowed_paths": ["src/**", "tests/**"],
                    "blocked_paths": [".env"],
                    "status": "pending",
                }
            ],
        }
        mc_results = root / "mc-results"
        mc_results.mkdir()
        (mc_results / "T010-worker-fizzbuzz.json").write_text(
            json.dumps(
                {
                    "task_id": "T010",
                    "role": "Worker",
                    "status": "completed",
                    "files_changed": [
                        f"{mc_state}/results/T010-worker-fizzbuzz.json",
                        f"{mc_state}/results/T010-worker-fizzbuzz.md",
                        "src/fizzbuzz.py",
                    ],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        mc_report = audit(mc_ownership, load_result_changes(mc_results), [], strict=False)
        if not mc_report["ok"]:
            errors.append(f"mission-control result paths should not fail audit, got {mc_report}")
        if any(item.get("reason") == "Outside allowed_paths" for item in mc_report["violations"]):
            errors.append("mission-control paths in files_changed must not trigger Outside allowed_paths")

        verifier_thin = {
            "task_id": "T011",
            "role": "Verifier",
            "status": "completed",
            "required_paths_verified": True,
            "required_paths_missing": [],
            "files_read": [],
            "files_changed": [],
        }
        verifier_results = root / "verifier-thin-results"
        verifier_results.mkdir()
        (verifier_results / "T011-verifier-thin.json").write_text(
            json.dumps(verifier_thin, indent=2),
            encoding="utf-8",
        )
        verifier_ownership = {
            "schema_version": 1,
            "tasks": [
                {
                    "task_id": "T011",
                    "session_name": "verifier-thin",
                    "role": "Verifier",
                    "allowed_paths": ["**/*"],
                    "required_paths": ["src/**", "tests/**"],
                    "blocked_paths": [".env"],
                    "status": "pending",
                }
            ],
        }
        verifier_report = audit(verifier_ownership, load_result_changes(verifier_results), [], strict=False)
        if verifier_report["ok"]:
            errors.append("expected audit failure for Verifier thin evidence (empty files_read)")
        thin_violations = [item for item in verifier_report["violations"] if "Thin evidence" in item.get("reason", "")]
        if not thin_violations:
            errors.append("expected Verifier thin evidence violation in audit report")
        if not any("thin_evidence" in str(item.get("detail", "")) for item in thin_violations):
            errors.append("Verifier thin evidence detail must mention thin_evidence")

        tools_results = root / "tools-results"
        tools_results.mkdir()
        (tools_results / "T012-worker-tools.json").write_text(
            json.dumps(
                {
                    "task_id": "T012",
                    "role": "Worker",
                    "status": "completed",
                    "files_changed": ["src/app.py"],
                    "tools_used": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        tools_ownership = {
            "schema_version": 1,
            "tasks": [
                {
                    "task_id": "T012",
                    "session_name": "worker-tools",
                    "role": "Worker",
                    "allowed_paths": ["src/**"],
                    "required_paths": ["src/**"],
                    "blocked_paths": [".env"],
                    "tools_used": ["git_tool"],
                    "status": "pending",
                }
            ],
        }
        tools_report = audit(tools_ownership, load_result_changes(tools_results), ["src/app.py"], strict=False)
        if not any(item.get("reason") == "missing_tools_used" for item in tools_report.get("warnings", [])):
            errors.append("expected missing_tools_used warning (not violation)")

        with tempfile.TemporaryDirectory(prefix="openclaw-audit-write-") as write_tmp:
            write_root = Path(write_tmp) / ".codex-multi-agent"
            write_root.mkdir()
            sample = audit(ownership, load_result_changes(results_dir), [], strict=False)
            audit_file = write_audit_report(sample, write_root)
            if not audit_file.exists():
                errors.append("write_audit_report did not create audit file")
            latest = write_root / "audits" / "latest.json"
            if not latest.exists():
                errors.append("write_audit_report did not create latest.json")
            saved = json.loads(audit_file.read_text(encoding="utf-8"))
            if "main_next_steps" not in saved or "gate" not in saved:
                errors.append("audit JSON missing main_next_steps or gate")
            if "changed_files_digest" not in saved:
                errors.append("audit JSON missing changed_files_digest metadata")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "audit_worker_output self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="Run built-in validation and exit")
    parser.add_argument("--ownership", help="Path to ownership.json")
    parser.add_argument("--results", help="Directory containing JSON and/or markdown result reports")
    parser.add_argument("--changed-files", help="Plain text changed-file list, one path per line")
    parser.add_argument("--strict", action="store_true", help="Treat missing reports and unowned global changes as violations")
    parser.add_argument("--write-audit", action="store_true", help="Write audit JSON under state_dir/audits/")
    parser.add_argument("--state-dir", default=".codex-multi-agent", help="Mission control directory for --write-audit")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    if not args.ownership:
        parser.error("--ownership is required unless --self-check is used")

    ownership_path = Path(args.ownership)
    ownership = json.loads(ownership_path.read_text(encoding="utf-8-sig"))
    result_changes = load_result_changes(Path(args.results) if args.results else None)
    global_changed = load_changed_files(Path(args.changed_files) if args.changed_files else None)

    report = audit(ownership, result_changes, global_changed, strict=args.strict)
    audit_path = None
    if args.write_audit:
        changed_path = Path(args.changed_files) if args.changed_files else Path(args.state_dir) / "changed-files.txt"
        audit_path = write_audit_report(report, Path(args.state_dir), changed_files_path=changed_path)
        report = {**report, "audit_path": str(audit_path), "latest_audit_path": str(Path(args.state_dir) / "audits" / "latest.json")}
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
