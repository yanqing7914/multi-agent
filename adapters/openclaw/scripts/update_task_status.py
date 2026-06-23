#!/usr/bin/env python3
"""Mission-control helper for OpenClaw v1 local state under .codex-multi-agent/."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from _preflight import (
    audit_stale_reason,
    changed_files_digest,
    changed_files_metadata,
    effective_status_issues,
    false_completion_reason,
    missing_result_report_reason,
)

VALID_STATUSES = {"pending", "running", "completed", "blocked", "failed"}


def memory_md_path_for_state(state_dir: Path, ownership: dict) -> Path:
    workspace_root = ownership.get("workspace_root") or ownership.get("target_repo")
    if workspace_root:
        return Path(workspace_root).expanduser().resolve() / "MEMORY.md"
    return state_dir.parent.resolve() / "MEMORY.md"


def memory_body_line_count(memory_path: Path) -> int:
    """Count append-only log lines (exclude headers and blanks)."""
    if not memory_path.exists():
        return 0
    count = 0
    for line in memory_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        count += 1
    return count
ROLE_ORDER = ("Explorer", "Worker", "Reviewer", "Verifier")
GATE_DEFS = (
    ("explorers_complete", "Explorer"),
    ("workers_complete", "Worker"),
    ("review_complete", "Reviewer"),
    ("verify_complete", "Verifier"),
    ("scope_audit", None),
    ("final_delivery", None),
)

RESULT_SCALAR_FIELDS = {
    "task_id",
    "session_name",
    "role",
    "status",
    "summary",
    "handoff_notes",
    "workspace_observed",
    "required_paths_verified",
}
RESULT_LIST_FIELDS = {
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


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


def parse_markdown_result(text: str) -> dict:
    data: dict = {}
    current_list: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        if re.match(r"^\s+- ", line) and current_list in RESULT_LIST_FIELDS:
            data.setdefault(current_list, []).append(line.strip()[2:].strip().strip('"\''))
            continue
        current_list = None
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in RESULT_SCALAR_FIELDS:
            data[key] = value.strip('"').strip("'")
            continue
        if key in RESULT_LIST_FIELDS and not value:
            current_list = key
            data.setdefault(key, [])
    return data


def load_result_data(path: Path) -> dict | None:
    if not path.exists():
        return None
    if path.suffix.lower() == ".json":
        try:
            data = read_json(path)
        except json.JSONDecodeError:
            return None
        return data if isinstance(data, dict) else None
    if path.suffix.lower() == ".md":
        return parse_markdown_result(path.read_text(encoding="utf-8-sig"))
    return None


def effective_status_from_result(
    result_path: Path,
    required_paths: list[str] | None = None,
    expected_workspace: str | None = None,
) -> tuple[str | None, dict]:
    data = load_result_data(result_path)
    if not data:
        return None, {}

    raw_status = str(data.get("status", "")).strip()
    status = raw_status if raw_status in VALID_STATUSES else None
    if raw_status and raw_status not in VALID_STATUSES:
        # treat unknown / template-leftover status tokens as blocked, not completed
        return "blocked", {
            "false_completion": True,
            "invalid_status_token": True,
            "reported_status": raw_status,
            "reason": f"invalid_status_token: {raw_status!r} is not in {sorted(VALID_STATUSES)}",
        }

    blocked_status, meta = effective_status_issues(data, required_paths, expected_workspace)
    if blocked_status:
        return blocked_status, meta

    return status, {}


def infer_status_from_result(result_path: Path) -> str | None:
    status, _ = effective_status_from_result(result_path)
    return status


def task_ids_for_role(tasks: list[dict], role: str | None) -> list[str]:
    if role is None:
        return []
    return [task["task_id"] for task in tasks if task.get("role") == role]


def gate_status(required_ids: list[str], task_statuses: dict[str, str]) -> str:
    if not required_ids:
        return "passed"
    statuses = [task_statuses.get(task_id, "pending") for task_id in required_ids]
    if any(status in {"blocked", "failed"} for status in statuses):
        return "failed"
    if all(status == "completed" for status in statuses):
        return "passed"
    if any(status in {"running", "completed"} for status in statuses):
        return "running"
    return "pending"


def annotate_dependencies(
    tasks: list[dict],
    task_statuses: dict[str, str],
    task_entries: dict[str, dict],
) -> None:
    """Surface the runtime dependency graph on each status entry (additive).

    Reads the static ``dependencies`` persisted on each ownership task and
    derives, per task:
      - ``dependencies``: the declared prerequisite task ids,
      - ``blocked_by``: prerequisites not yet ``completed`` (empty => unblocked),
      - ``ready_to_spawn``: pending AND not blocked (auto-unblock signal).

    This is purely informational for Main / launchers; it does NOT change gate
    pass/fail computation, so existing gate behavior is untouched.
    """
    known_ids = {task.get("task_id") for task in tasks}
    for task in tasks:
        task_id = task.get("task_id")
        entry = task_entries.get(task_id)
        if entry is None:
            continue
        deps = [dep for dep in (task.get("dependencies") or []) if dep in known_ids]
        blocked_by = [dep for dep in deps if task_statuses.get(dep) != "completed"]
        entry["dependencies"] = deps
        entry["blocked_by"] = blocked_by
        entry["ready_to_spawn"] = task_statuses.get(task_id) == "pending" and not blocked_by


def readiness_report(status_doc: dict) -> dict:
    """Summarize which tasks are ready to spawn vs blocked, from a synced status doc.

    Consumes the additive ``ready_to_spawn`` / ``blocked_by`` fields written by
    ``annotate_dependencies`` so Main / loops can pick the next unblocked task
    without re-deriving the graph.
    """
    ready: list[str] = []
    blocked: dict[str, list[str]] = {}
    for task_id, entry in (status_doc.get("tasks") or {}).items():
        if entry.get("ready_to_spawn"):
            ready.append(task_id)
        blocking = entry.get("blocked_by") or []
        if blocking:
            blocked[task_id] = blocking
    return {"ready": sorted(ready), "blocked": blocked}


def build_gates(
    tasks: list[dict],
    task_statuses: dict[str, str],
    audit_gate: str | None,
    audit_meta: dict | None = None,
) -> dict:
    audit_meta = audit_meta or {}
    gates: dict[str, dict] = {}
    for gate_name, role in GATE_DEFS:
        required = task_ids_for_role(tasks, role) if role else []
        completed = [task_id for task_id in required if task_statuses.get(task_id) == "completed"]
        if gate_name == "scope_audit":
            status = audit_gate if audit_gate else "pending"
            note = "Run audit_worker_output.py and write audit JSON under audits/"
            if audit_meta.get("stale"):
                note = f"Stale audit: {audit_meta.get('stale_reason')}. Recapture changed-files.txt and rerun audit."
            gates[gate_name] = {
                "status": status,
                "required_task_ids": [],
                "completed_task_ids": [],
                "note": note,
            }
        elif gate_name == "final_delivery":
            upstream = [name for name, _ in GATE_DEFS if name not in {"final_delivery"}]
            upstream_passed = all(gates.get(name, {}).get("status") == "passed" for name in upstream)
            status = "passed" if upstream_passed else "pending"
            gates[gate_name] = {
                "status": status,
                "required_task_ids": [],
                "completed_task_ids": [],
                "note": "Main delivers after all upstream gates pass",
            }
        else:
            gates[gate_name] = {
                "status": gate_status(required, task_statuses),
                "required_task_ids": required,
                "completed_task_ids": completed,
            }
    return gates


def current_phase(gates: dict) -> str:
    for gate_name, _ in GATE_DEFS:
        if gates.get(gate_name, {}).get("status") != "passed":
            return gate_name
    return "final_delivery"


def load_latest_audit(audits_dir: Path) -> tuple[dict | None, Path | None]:
    if not audits_dir.exists():
        return None, None
    audit_files = sorted(audits_dir.glob("audit-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not audit_files:
        latest = audits_dir / "latest.json"
        if latest.exists():
            audit_files = [latest]
        else:
            return None, None
    audit_path = audit_files[0]
    try:
        report = read_json(audit_path)
    except json.JSONDecodeError:
        return None, audit_path
    if not isinstance(report, dict):
        return None, audit_path
    return report, audit_path


def resolve_scope_audit(state_dir: Path, audits_dir: Path) -> dict:
    """Derive scope_audit gate from latest audit JSON and changed-files freshness."""
    report, audit_path = load_latest_audit(audits_dir)
    if report is None:
        return {
            "gate_status": None,
            "ok": None,
            "stale": False,
            "stale_reason": None,
            "audit_path": str(audit_path) if audit_path else None,
        }

    gate = report.get("gate", {})
    gate_status = gate.get("status") if isinstance(gate, dict) else None
    if gate_status not in {"passed", "failed", "pending"}:
        gate_status = "passed" if report.get("ok") is True else "failed" if report.get("ok") is False else "pending"

    ok = report.get("ok")
    if ok is None:
        ok = gate_status == "passed"

    stale_reason = audit_stale_reason(state_dir, report, audit_path)
    if stale_reason:
        return {
            "gate_status": "pending",
            "ok": False,
            "stale": True,
            "stale_reason": stale_reason,
            "audit_path": str(audit_path) if audit_path else None,
        }

    return {
        "gate_status": gate_status,
        "ok": bool(ok) if gate_status == "passed" else False,
        "stale": False,
        "stale_reason": None,
        "audit_path": str(audit_path) if audit_path else None,
    }


def latest_audit_ok(audits_dir: Path, state_dir: Path | None = None) -> bool | None:
    if state_dir is None:
        gate = latest_audit_gate(audits_dir)
        return None if gate is None else gate == "passed"
    resolved = resolve_scope_audit(state_dir, audits_dir)
    return resolved["ok"]


def latest_audit_gate(audits_dir: Path, state_dir: Path | None = None) -> str | None:
    if state_dir is None:
        report, _ = load_latest_audit(audits_dir)
        if report is None:
            return None
        gate = report.get("gate", {})
        if isinstance(gate, dict) and gate.get("status") in {"passed", "failed", "pending"}:
            return gate["status"]
        return "passed" if report.get("ok") is True else "failed" if report.get("ok") is False else "pending"
    return resolve_scope_audit(state_dir, audits_dir)["gate_status"]


MCP_FINDING_SOURCES = {"mcp", "record_finding"}


def merge_findings(existing: list[dict], collected: list[dict]) -> list[dict]:
    """Preserve MCP-appended findings when sync_status rebuilds reviewer findings."""
    mcp_findings = [item for item in existing if item.get("source") in MCP_FINDING_SOURCES]
    merged = list(collected)
    seen = {
        (
            item.get("title"),
            item.get("task_id"),
            item.get("severity", "P2"),
            item.get("source"),
        )
        for item in merged
    }
    for item in mcp_findings:
        key = (
            item.get("title"),
            item.get("task_id"),
            item.get("severity", "P2"),
            item.get("source"),
        )
        if key in seen:
            continue
        merged.append(item)
        seen.add(key)
    return merged


def collect_findings(results_dir: Path, tasks: list[dict]) -> list[dict]:
    findings: list[dict] = []
    reviewer_ids = {task["task_id"] for task in tasks if task.get("role") == "Reviewer"}
    if not results_dir.exists():
        return findings
    for result_file in sorted(results_dir.iterdir()):
        if result_file.suffix.lower() not in {".json", ".md"}:
            continue
        task_id_match = re.match(r"^(T\d+)-", result_file.stem)
        if not task_id_match:
            continue
        task_id = task_id_match.group(1)
        if task_id not in reviewer_ids:
            continue
        if result_file.suffix.lower() == ".json":
            try:
                data = read_json(result_file)
            except json.JSONDecodeError as exc:
                findings.append({
                    "task_id": task_id,
                    "severity": "P3",
                    "title": "Malformed reviewer JSON skipped during sync",
                    "evidence": [f"{result_file}: {exc}"],
                    "source": "collect_findings",
                })
                continue
            if not isinstance(data, dict):
                continue
            for item in data.get("findings", []):
                if isinstance(item, dict):
                    findings.append({"task_id": task_id, "source": "collect_findings", **item})
                elif isinstance(item, str):
                    findings.append({"task_id": task_id, "title": item, "severity": "P2", "source": "collect_findings"})
            continue
        for line in result_file.read_text(encoding="utf-8-sig").splitlines():
            stripped = line.strip()
            if stripped.startswith("- severity:") or stripped.startswith("- title:"):
                findings.append({"task_id": task_id, "raw": stripped.lstrip("- ").strip()})
    return findings


def sync_status(state_dir: Path) -> dict:
    ownership_path = state_dir / "ownership.json"
    if not ownership_path.exists():
        raise FileNotFoundError(f"Missing ownership.json in {state_dir}")

    ownership = read_json(ownership_path)
    tasks = ownership.get("tasks", [])
    expected_workspace = ownership.get("workspace_root") or ownership.get("target_repo")
    results_dir = state_dir / "results"
    audits_dir = state_dir / "audits"
    findings_dir = state_dir / "findings"
    approvals_dir = state_dir / "approvals"

    for directory in (results_dir, findings_dir, approvals_dir, audits_dir):
        directory.mkdir(parents=True, exist_ok=True)

    task_statuses: dict[str, str] = {}
    task_entries: dict[str, dict] = {}
    preflight_issues: list[dict] = []
    for task in tasks:
        task_id = task["task_id"]
        json_path = Path(task.get("result_report_json", ""))
        md_path = Path(task.get("result_report_markdown", ""))
        req_paths = task.get("required_paths") or []
        json_status, json_meta = effective_status_from_result(json_path, req_paths, expected_workspace)
        md_status, md_meta = effective_status_from_result(md_path, req_paths, expected_workspace)
        inferred = None
        preflight_meta: dict = {}
        if json_path.exists() and json_status and not json_meta:
            # JSON report exists and is clean; ignore markdown (markdown parser may miss fields)
            inferred = json_status
        elif json_meta or md_meta:
            preflight_meta = json_meta or md_meta
            inferred = json_status if json_meta else md_status
            if not inferred:
                inferred = "blocked"
        else:
            inferred = json_status or md_status
        missing_report_reason = missing_result_report_reason(task, json_path, md_path)
        if missing_report_reason:
            reported_status = inferred or task.get("status", "completed")
            inferred = "blocked"
            preflight_meta = {
                "missing_result_report": True,
                "reported_status": reported_status,
                "reason": missing_report_reason,
                "result_report_json": str(json_path),
                "result_report_markdown": str(md_path),
            }
        status = inferred or task.get("status", "pending")
        if status not in VALID_STATUSES:
            status = "pending"
        task_statuses[task_id] = status
        entry = {
            "task_id": task_id,
            "session_name": task.get("session_name"),
            "role": task.get("role"),
            "status": status,
            "updated_at": utc_now(),
            "result_report_json": task.get("result_report_json"),
            "result_report_markdown": task.get("result_report_markdown"),
        }
        if preflight_meta:
            entry["preflight"] = preflight_meta
            preflight_issues.append(
                {
                    "task_id": task_id,
                    "session_name": task.get("session_name"),
                    "role": task.get("role"),
                    **preflight_meta,
                }
            )
        task_entries[task_id] = entry
        task["status"] = status

    annotate_dependencies(tasks, task_statuses, task_entries)

    audit_meta = resolve_scope_audit(state_dir, audits_dir)
    audit_ok = audit_meta["ok"]
    audit_gate = audit_meta["gate_status"]
    gates = build_gates(tasks, task_statuses, audit_gate, audit_meta)
    findings = collect_findings(results_dir, tasks)
    findings_path = findings_dir / "review-findings.json"
    existing_findings: list[dict] = []
    if findings_path.exists():
        try:
            existing_findings = read_json(findings_path).get("findings", [])
        except json.JSONDecodeError:
            existing_findings = []
    findings = merge_findings(existing_findings, findings)
    write_json(findings_path, {"schema_version": 1, "updated_at": utc_now(), "findings": findings})

    existing = {}
    status_path = state_dir / "status.json"
    if status_path.exists():
        try:
            existing = read_json(status_path)
        except json.JSONDecodeError:
            existing = {}

    status_doc = {
        "schema_version": 1,
        "run_id": existing.get("run_id") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "task_title": ownership.get("task", ""),
        "state_dir": str(state_dir),
        "workspace_root": expected_workspace or existing.get("workspace_root"),
        "target_repo": ownership.get("target_repo") or expected_workspace or existing.get("target_repo"),
        "adapter_root": ownership.get("adapter_root") or existing.get("adapter_root"),
        "generated_at": existing.get("generated_at") or ownership.get("generated_at") or utc_now(),
        "updated_at": utc_now(),
        "current_phase": current_phase(gates),
        "gates": gates,
        "tasks": task_entries,
        "latest_audit": {
            "ok": audit_ok,
            "gate_status": audit_gate,
            "stale": audit_meta.get("stale", False),
            "stale_reason": audit_meta.get("stale_reason"),
            "audit_path": audit_meta.get("audit_path"),
            "findings_file": str(findings_path),
        },
        "preflight_issues": preflight_issues,
    }
    write_json(status_path, status_doc)
    ownership["updated_at"] = utc_now()
    write_json(ownership_path, ownership)
    return status_doc


def update_task(state_dir: Path, task_id: str, status: str, note: str | None) -> dict:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {status}")

    ownership_path = state_dir / "ownership.json"
    status_path = state_dir / "status.json"
    if not ownership_path.exists():
        raise FileNotFoundError(f"Missing ownership.json in {state_dir}")

    ownership = read_json(ownership_path)
    matched = False
    for task in ownership.get("tasks", []):
        if task.get("task_id") == task_id:
            task["status"] = status
            if note:
                task["note"] = note
            matched = True
            break
    if not matched:
        raise KeyError(f"Task {task_id} not found in ownership.json")

    write_json(ownership_path, ownership)

    status_doc = read_json(status_path) if status_path.exists() else {}
    task_entries = status_doc.setdefault("tasks", {})
    entry = task_entries.setdefault(task_id, {"task_id": task_id})
    entry["status"] = status
    entry["updated_at"] = utc_now()
    if note:
        entry["note"] = note
    status_doc["updated_at"] = utc_now()
    write_json(status_path, status_doc)

    return sync_status(state_dir)


def summarize_run(state_dir: Path, out_path: Path | None) -> dict:
    status_doc = sync_status(state_dir)
    ownership = read_json(state_dir / "ownership.json")
    findings_doc = read_json(state_dir / "findings" / "review-findings.json")

    lines = [
        "# Multi-Agent Run Summary",
        "",
        f"Task: {ownership.get('task', '')}",
        f"Run ID: {status_doc.get('run_id', '')}",
        f"Current phase: {status_doc.get('current_phase', '')}",
        "",
        "## Gate Status",
        "",
    ]
    for gate_name, gate in status_doc.get("gates", {}).items():
        lines.append(f"- {gate_name}: {gate.get('status', 'pending')}")

    lines.extend(["", "## Tasks", ""])
    for task in ownership.get("tasks", []):
        status_entry = status_doc.get("tasks", {}).get(task.get("task_id"), {})
        line = f"- {task.get('task_id')} ({task.get('role')} / {task.get('session_name')}): {task.get('status', 'pending')}"
        blocked_by = status_entry.get("blocked_by") or []
        if blocked_by:
            line += f" [blocked_by: {', '.join(blocked_by)}]"
        elif status_entry.get("ready_to_spawn"):
            line += " [ready_to_spawn]"
        preflight = status_entry.get("preflight")
        if preflight:
            line += f" [false completion blocked: {preflight.get('reason', 'required paths not verified')}]"
        lines.append(line)

    preflight_issues = status_doc.get("preflight_issues", [])
    lines.extend(["", "## Workspace / Preflight Issues", ""])
    if preflight_issues:
        for item in preflight_issues:
            lines.append(
                f"- {item.get('task_id')} ({item.get('session_name')}): reported completed but treated as blocked — {item.get('reason')}"
            )
    else:
        lines.append("- None recorded")

    findings = findings_doc.get("findings", [])
    lines.extend(["", "## Review Findings", ""])
    if findings:
        for item in findings:
            if isinstance(item, dict):
                title = item.get("title") or item.get("raw") or json.dumps(item, ensure_ascii=False)
                severity = item.get("severity", "P2")
                lines.append(f"- [{severity}] {title}")
            else:
                lines.append(f"- {item}")
    else:
        lines.append("- None recorded")

    latest_audit = status_doc.get("latest_audit", {})
    audit_ok = latest_audit.get("ok")
    lines.extend(
        [
            "",
            "## Scope Audit",
            "",
            f"- Latest audit ok: {audit_ok if audit_ok is not None else 'not run'}",
            f"- Gate status: {latest_audit.get('gate_status', 'not run')}",
        ]
    )
    if latest_audit.get("stale"):
        lines.append(f"- Stale: {latest_audit.get('stale_reason', 'changed-files.txt out of date')}")
    lines.extend(["", "## Main Next Steps", ""])
    current = status_doc.get("current_phase", "explorers_complete")
    next_steps = {
        "explorers_complete": "Collect Explorer reports, then spawn Workers.",
        "workers_complete": "Capture git diff, run audit_worker_output.py --write-audit, then spawn Reviewers.",
        "review_complete": "Triage findings in findings/review-findings.json, then spawn Verifier.",
        "verify_complete": "Run scope audit if not done, perform diff audit, prepare final delivery.",
        "scope_audit": "Fix violations/conflicts, rerun audit, then finalize delivery.",
        "final_delivery": "Deliver using templates/final-delivery.md.",
    }
    lines.append(f"- {next_steps.get(current, 'Review status.json and continue the workflow.')}")

    summary_text = "\n".join(lines) + "\n"
    target = out_path or (state_dir / "summary" / "run-summary.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(summary_text, encoding="utf-8")

    memory_result = None
    memory_lines_before = memory_body_line_count(memory_md_path_for_state(state_dir, ownership))
    memory_script = Path(__file__).resolve().parent / "memory_log.py"
    memory_update_error: str | None = None
    memory_lines_added = 0
    if memory_script.exists():
        import subprocess

        proc = subprocess.run(
            [
                sys.executable,
                str(memory_script),
                "--state-dir",
                str(state_dir),
                "--from-run",
                "--exclude-session",
                "reviewer-false-demo",
                "--exclude-session",
                "reviewer-thin-demo",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                memory_result = json.loads(proc.stdout)
            except json.JSONDecodeError:
                memory_result = {"ok": False, "stderr": proc.stderr}
        elif proc.returncode != 0:
            memory_result = {"ok": False, "stderr": (proc.stderr or proc.stdout or "").strip()}

        memory_path = memory_md_path_for_state(state_dir, ownership)
        memory_lines_after = memory_body_line_count(memory_path)
        memory_lines_added = max(0, memory_lines_after - memory_lines_before)
        if memory_result and memory_result.get("ok") and memory_lines_added >= 1:
            print(f"MEMORY.md updated: +{memory_lines_added} lines")
        else:
            memory_update_error = (
                "MEMORY.md summarize did not append a new line "
                f"(before={memory_lines_before}, after={memory_lines_after}, "
                f"memory_log_ok={bool(memory_result and memory_result.get('ok'))})"
            )
    else:
        memory_update_error = "memory_log.py not found; cannot append MEMORY.md"

    rotation_result = None
    rotate_script = Path(__file__).resolve().parent / "memory_rotate.py"
    if rotate_script.exists():
        import subprocess

        workspace_root = ownership.get("workspace_root") or ownership.get("target_repo")
        memory_path = Path(workspace_root) / "MEMORY.md" if workspace_root else Path(__file__).resolve().parent.parent.parent.parent / "MEMORY.md"
        rot_proc = subprocess.run(
            [sys.executable, str(rotate_script), "--memory-path", str(memory_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if rot_proc.stdout.strip():
            try:
                rotation_result = json.loads(rot_proc.stdout)
            except json.JSONDecodeError:
                rotation_result = {"ok": False, "stderr": rot_proc.stderr}
        elif rot_proc.returncode != 0:
            rotation_result = {"ok": False, "stderr": rot_proc.stderr}

    payload = {
        "ok": memory_update_error is None,
        "summary_path": str(target),
        "current_phase": status_doc.get("current_phase"),
        "gates": status_doc.get("gates"),
        "memory": memory_result,
        "memory_lines_added": memory_lines_added,
        "memory_rotation": rotation_result,
    }
    if memory_update_error:
        payload["memory_update_error"] = memory_update_error
    return payload


def run_self_check() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="openclaw-status-") as tmp:
        state_dir = Path(tmp) / ".codex-multi-agent"
        state_dir.mkdir()
        tasks_dir = state_dir / "tasks"
        results_dir = state_dir / "results"
        tasks_dir.mkdir()
        results_dir.mkdir()

        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        ownership = {
            "schema_version": 1,
            "generated_at": utc_now(),
            "task": "Self-check run",
            "workspace_root": str(workspace),
            "state_dir": str(state_dir),
            "tasks": [
                {
                    "task_id": "T001",
                    "session_name": "explorer-backend",
                    "role": "Explorer",
                    "mode": "research",
                    "runtime": "subagent",
                    "write_permission": False,
                    "allowed_paths": ["backend/**"],
                    "blocked_paths": [".env"],
                    "result_report_json": str(results_dir / "T001-explorer-backend.json"),
                    "result_report_markdown": str(results_dir / "T001-explorer-backend.md"),
                    "status": "pending",
                },
                {
                    "task_id": "T002",
                    "session_name": "worker-backend",
                    "role": "Worker",
                    "mode": "implement",
                    "runtime": "acp",
                    "write_permission": True,
                    "allowed_paths": ["backend/**"],
                    "blocked_paths": [".env"],
                    "result_report_json": str(results_dir / "T002-worker-backend.json"),
                    "result_report_markdown": str(results_dir / "T002-worker-backend.md"),
                    "status": "pending",
                },
            ],
        }
        write_json(state_dir / "ownership.json", ownership)
        write_json(
            state_dir / "status.json",
            {
                "run_id": "SELFCHK001",
                "gates": {"explorers_complete": {"status": "pending"}},
                "latest_audit": {"ok": False, "gate_status": "pending"},
            },
        )

        synced = sync_status(state_dir)
        if synced["current_phase"] != "explorers_complete":
            errors.append(f"expected explorers_complete phase, got {synced['current_phase']}")

        (results_dir / "T001-explorer-backend.json").write_text(
            json.dumps({"task_id": "T001", "role": "Explorer", "status": "completed", "files_changed": []}),
            encoding="utf-8",
        )
        synced = sync_status(state_dir)
        if synced["gates"]["explorers_complete"]["status"] != "passed":
            errors.append("explorer gate should pass after result report")

        updated = update_task(state_dir, "T002", "running", "Worker spawned")
        if updated["tasks"]["T002"]["status"] != "running":
            errors.append("update_task did not persist running status")

        summary = summarize_run(state_dir, None)
        summary_path = Path(summary["summary_path"])
        if not summary_path.exists():
            errors.append("summarize_run did not write summary markdown")
        if not summary.get("ok"):
            errors.append(f"summarize_run memory self-check failed: {summary.get('memory_update_error')}")
        elif summary.get("memory_lines_added", 0) < 1:
            errors.append("summarize_run must append at least one MEMORY.md line")

        mem_fail_state = Path(tmp) / "mem-fail"
        mem_fail_state.mkdir()
        mem_fail_workspace = Path(tmp) / "mem-fail-ws"
        mem_fail_workspace.mkdir()
        write_json(
            mem_fail_state / "ownership.json",
            {"task": "memory fail", "workspace_root": str(mem_fail_workspace), "tasks": []},
        )
        import subprocess

        mem_script = Path(__file__).resolve().parent / "memory_log.py"
        before_fail = memory_body_line_count(mem_fail_workspace / "MEMORY.md")
        fail_proc = subprocess.run(
            [sys.executable, str(mem_script), "--state-dir", str(mem_fail_state), "--from-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        fail_payload = json.loads(fail_proc.stdout) if fail_proc.stdout.strip() else {}
        after_fail = memory_body_line_count(mem_fail_workspace / "MEMORY.md")
        if fail_payload.get("ok"):
            errors.append("memory_log --from-run without status.json must return ok=false")
        if after_fail > before_fail:
            errors.append("MEMORY.md must not grow when status.json is missing")

        ro_state = Path(tmp) / "mem-ro"
        ro_state.mkdir()
        ro_ws = Path(tmp) / "mem-ro-ws"
        ro_ws.mkdir()
        ro_memory = ro_ws / "MEMORY.md"
        ro_memory.write_text("# Project Memory\n\n", encoding="utf-8")
        ro_memory.chmod(0o444)
        write_json(
            ro_state / "ownership.json",
            {"task": "read-only memory", "workspace_root": str(ro_ws), "tasks": []},
        )
        write_json(ro_state / "status.json", {"run_id": "RO001", "gates": {}, "latest_audit": {}})
        ro_proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--state-dir", str(ro_state), "--summarize"],
            capture_output=True,
            text=True,
            check=False,
        )
        ro_memory.chmod(0o644)
        if ro_proc.returncode == 0:
            errors.append("--summarize must exit non-zero when MEMORY.md cannot be appended")

        audits_dir = state_dir / "audits"
        audits_dir.mkdir(exist_ok=True)
        write_json(
            audits_dir / "audit-test.json",
            {"ok": True, "gate": {"id": "scope_audit", "status": "passed"}, "violations": [], "conflicts": [], "warnings": [], "summary": {}},
        )
        synced = sync_status(state_dir)
        if synced["gates"]["scope_audit"]["status"] != "passed":
            errors.append("scope_audit gate should pass when latest audit ok=true")

        changed_path = state_dir / "changed-files.txt"
        changed_path.write_text("backend/src/app.py\n", encoding="utf-8")
        digest = changed_files_digest(["backend/src/app.py"])
        write_json(
            audits_dir / "audit-fresh.json",
            {
                "schema_version": 1,
                "generated_at": utc_now(),
                "ok": True,
                "changed_files_digest": digest,
                "changed_files_mtime": changed_path.stat().st_mtime,
                "gate": {"id": "scope_audit", "status": "passed"},
                "violations": [],
                "conflicts": [],
                "warnings": [],
            },
        )
        fresh_sync = sync_status(state_dir)
        if fresh_sync["gates"]["scope_audit"]["status"] != "passed":
            errors.append("scope_audit should pass when audit digest matches changed-files.txt")
        changed_path.write_text("backend/src/other.py\n", encoding="utf-8")
        stale_sync = sync_status(state_dir)
        if stale_sync["gates"]["scope_audit"]["status"] != "pending":
            errors.append("scope_audit must be pending when changed-files.txt differs from audit digest")
        if not stale_sync.get("latest_audit", {}).get("stale"):
            errors.append("latest_audit.stale should be true after changed-files change")
        if stale_sync.get("latest_audit", {}).get("ok") is not False:
            errors.append("stale audit must not report latest_audit.ok=true")

        changed_path.write_text("backend/src/app.py\n", encoding="utf-8")
        warn_audit = {
            "ok": False,
            "gate": {"id": "scope_audit", "status": "pending"},
            "violations": [],
            "conflicts": [],
            "warnings": [{"reason": "Worker result report not found"}],
            "changed_files_digest": digest,
            "changed_files_mtime": changed_path.stat().st_mtime,
        }
        write_json(audits_dir / "audit-warn.json", warn_audit)
        warn_sync = sync_status(state_dir)
        if warn_sync["gates"]["scope_audit"]["status"] != "pending":
            errors.append("scope_audit gate must stay pending when audit has warnings (ok=false)")
        if warn_sync.get("latest_audit", {}).get("ok") is not False:
            errors.append("latest_audit.ok must be false when audit gate is pending")

        reviewer_result = {
            "task_id": "T003",
            "session_name": "reviewer-correctness",
            "role": "Reviewer",
            "status": "completed",
            "required_paths_verified": False,
            "required_paths_missing": ["adapters/openclaw/**"],
            "workspace_observed": "/tmp/wrong-workspace",
            "files_changed": [],
            "findings": [],
        }
        ownership["tasks"].append(
            {
                "task_id": "T003",
                "session_name": "reviewer-correctness",
                "role": "Reviewer",
                "mode": "review",
                "runtime": "subagent",
                "write_permission": False,
                "allowed_paths": ["**/*"],
                "required_paths": ["adapters/openclaw/**"],
                "blocked_paths": [".env"],
                "result_report_json": str(results_dir / "T003-reviewer-correctness.json"),
                "result_report_markdown": str(results_dir / "T003-reviewer-correctness.md"),
                "status": "pending",
            }
        )
        write_json(state_dir / "ownership.json", ownership)
        (results_dir / "T003-reviewer-correctness.json").write_text(
            json.dumps(reviewer_result, indent=2),
            encoding="utf-8",
        )
        false_sync = sync_status(state_dir)
        if false_sync["tasks"]["T003"]["status"] != "blocked":
            errors.append("completed report with required_paths_verified=false must sync as blocked")
        if false_sync["gates"]["review_complete"]["status"] == "passed":
            errors.append("review_complete gate must not pass when required paths were not verified")
        if not false_sync.get("preflight_issues"):
            errors.append("preflight_issues should be recorded for false completion")

        thin_result = {
            "task_id": "T004",
            "session_name": "reviewer-thin-evidence",
            "role": "Reviewer",
            "status": "completed",
            "required_paths_verified": True,
            "required_paths_missing": [],
            "required_paths_checked": ["adapters/openclaw/**"],
            "files_read": [],
            "files_changed": [],
        }
        ownership["tasks"].append(
            {
                "task_id": "T004",
                "session_name": "reviewer-thin-evidence",
                "role": "Reviewer",
                "mode": "review",
                "runtime": "subagent",
                "write_permission": False,
                "allowed_paths": ["**/*"],
                "required_paths": ["adapters/openclaw/**"],
                "blocked_paths": [".env"],
                "result_report_json": str(results_dir / "T004-reviewer-thin-evidence.json"),
                "result_report_markdown": str(results_dir / "T004-reviewer-thin-evidence.md"),
                "status": "pending",
            }
        )
        write_json(state_dir / "ownership.json", ownership)
        (results_dir / "T004-reviewer-thin-evidence.json").write_text(
            json.dumps(thin_result, indent=2),
            encoding="utf-8",
        )
        thin_sync = sync_status(state_dir)
        if thin_sync["tasks"]["T004"]["status"] != "blocked":
            errors.append("completed report with empty files_read must sync as blocked (thin evidence)")
        thin_issues = thin_sync.get("preflight_issues", [])
        if not any(
            issue.get("thin_evidence") and issue.get("role") == "Reviewer"
            for issue in thin_issues
            if issue.get("task_id") == "T004"
        ):
            errors.append("Reviewer thin evidence should surface thin_evidence in preflight_issues")

        verifier_thin_result = {
            "task_id": "T006",
            "session_name": "verifier-thin-evidence",
            "role": "Verifier",
            "status": "completed",
            "required_paths_verified": True,
            "required_paths_missing": [],
            "required_paths_checked": ["src/**", "tests/**"],
            "files_read": [],
            "files_changed": [],
            "commands_run": ["pytest"],
        }
        ownership["tasks"].append(
            {
                "task_id": "T006",
                "session_name": "verifier-thin-evidence",
                "role": "Verifier",
                "mode": "verify",
                "runtime": "subagent",
                "write_permission": False,
                "allowed_paths": ["**/*"],
                "required_paths": ["src/**", "tests/**"],
                "blocked_paths": [".env"],
                "result_report_json": str(results_dir / "T006-verifier-thin-evidence.json"),
                "result_report_markdown": str(results_dir / "T006-verifier-thin-evidence.md"),
                "status": "pending",
            }
        )
        write_json(state_dir / "ownership.json", ownership)
        (results_dir / "T006-verifier-thin-evidence.json").write_text(
            json.dumps(verifier_thin_result, indent=2),
            encoding="utf-8",
        )
        verifier_thin_sync = sync_status(state_dir)
        if verifier_thin_sync["tasks"]["T006"]["status"] != "blocked":
            errors.append("Verifier completed with empty files_read must sync as blocked (thin evidence)")
        verifier_issues = [
            issue
            for issue in verifier_thin_sync.get("preflight_issues", [])
            if issue.get("task_id") == "T006"
        ]
        if not any(issue.get("thin_evidence") for issue in verifier_issues):
            errors.append("Verifier thin evidence must surface thin_evidence in preflight_issues")
        if not any("Verifier" in str(issue.get("role", "")) or issue.get("role") == "Verifier" for issue in verifier_issues):
            errors.append("Verifier thin evidence preflight issue must identify Verifier role")

        mismatch_result = {
            "task_id": "T005",
            "session_name": "explorer-wrong-pwd",
            "role": "Explorer",
            "status": "completed",
            "workspace_observed": "/tmp/other-repo",
            "required_paths_verified": True,
            "files_read": ["backend/foo.py"],
            "files_changed": [],
        }
        ownership["tasks"].append(
            {
                "task_id": "T005",
                "session_name": "explorer-wrong-pwd",
                "role": "Explorer",
                "mode": "research",
                "runtime": "subagent",
                "write_permission": False,
                "allowed_paths": ["backend/**"],
                "required_paths": ["backend/**"],
                "blocked_paths": [".env"],
                "result_report_json": str(results_dir / "T005-explorer-wrong-pwd.json"),
                "result_report_markdown": str(results_dir / "T005-explorer-wrong-pwd.md"),
                "status": "pending",
            }
        )
        ownership["workspace_root"] = str(Path(tmp) / "target-repo")
        write_json(state_dir / "ownership.json", ownership)
        (results_dir / "T005-explorer-wrong-pwd.json").write_text(
            json.dumps(mismatch_result, indent=2),
            encoding="utf-8",
        )
        mismatch_sync = sync_status(state_dir)
        if mismatch_sync["tasks"]["T005"]["status"] != "blocked":
            errors.append("workspace_observed mismatch must sync as blocked")

        malformed_state = Path(tmp) / "malformed-reviewer-json"
        malformed_state.mkdir()
        malformed_results = malformed_state / "results"
        malformed_results.mkdir()
        write_json(malformed_state / "ownership.json", {
            "schema_version": 1,
            "task": "malformed reviewer JSON sync resilience",
            "workspace_root": str(malformed_state),
            "tasks": [
                {
                    "task_id": "T020",
                    "session_name": "reviewer-broken",
                    "role": "Reviewer",
                    "status": "pending",
                    "required_paths": [],
                    "result_report_json": str(malformed_results / "T020-reviewer-broken.json"),
                    "result_report_markdown": str(malformed_results / "T020-reviewer-broken.md"),
                }
            ],
        })
        (malformed_results / "T020-reviewer-broken.json").write_text("{not valid json", encoding="utf-8")
        try:
            malformed_synced = sync_status(malformed_state)
        except Exception as exc:
            errors.append(f"sync_status must tolerate malformed reviewer JSON, raised {exc}")
            malformed_synced = None
        if malformed_synced is not None:
            if malformed_synced["tasks"]["T020"]["status"] == "completed":
                errors.append("malformed reviewer JSON must not be treated as completed")
            if not (malformed_state / "status.json").exists():
                errors.append("sync_status must still write status.json when reviewer JSON is malformed")

        invalid_status_state = Path(tmp) / "invalid-status-token"
        invalid_status_state.mkdir()
        invalid_status_results = invalid_status_state / "results"
        invalid_status_results.mkdir()
        write_json(invalid_status_state / "ownership.json", {
            "schema_version": 1,
            "task": "invalid status token gating",
            "workspace_root": str(invalid_status_state),
            "tasks": [
                {
                    "task_id": "T030",
                    "session_name": "reviewer-token-leftover",
                    "role": "Reviewer",
                    "status": "pending",
                    "required_paths": [],
                    "result_report_json": str(invalid_status_results / "T030-reviewer-token-leftover.json"),
                    "result_report_markdown": str(invalid_status_results / "T030-reviewer-token-leftover.md"),
                }
            ],
        })
        (invalid_status_results / "T030-reviewer-token-leftover.json").write_text(
            json.dumps({
                "task_id": "T030",
                "role": "Reviewer",
                "status": "completed | blocked | failed",
                "required_paths_verified": True,
                "files_read": ["adapters/openclaw/SKILL.md"],
                "files_changed": [],
            }),
            encoding="utf-8",
        )
        invalid_token_synced = sync_status(invalid_status_state)
        if invalid_token_synced["tasks"]["T030"]["status"] == "completed":
            errors.append("invalid status token must not be coerced to completed")
        if invalid_token_synced["gates"]["review_complete"]["status"] == "passed":
            errors.append("review gate must not pass when reviewer reports invalid status token")
        if not any(issue.get("invalid_status_token") for issue in invalid_token_synced.get("preflight_issues", [])):
            errors.append("invalid status token should surface as preflight issue")

        no_report_state = Path(tmp) / "no-report-completed"
        no_report_state.mkdir()
        no_report_results = no_report_state / "results"
        no_report_results.mkdir()
        no_report_ownership = {
            "schema_version": 1,
            "task": "manual completion evidence gate",
            "workspace_root": str(no_report_state),
            "tasks": [
                {
                    "task_id": "T010",
                    "session_name": "reviewer-no-report",
                    "role": "Reviewer",
                    "status": "completed",
                    "required_paths": ["adapters/openclaw/**"],
                    "result_report_json": str(no_report_results / "T010-reviewer-no-report.json"),
                    "result_report_markdown": str(no_report_results / "T010-reviewer-no-report.md"),
                }
            ],
        }
        write_json(no_report_state / "ownership.json", no_report_ownership)
        no_report_synced = sync_status(no_report_state)
        if no_report_synced["tasks"]["T010"]["status"] == "completed":
            errors.append("metadata-only completed task must not sync as completed without result report")
        if no_report_synced["gates"]["review_complete"]["status"] == "passed":
            errors.append("review gate must not pass without result report evidence")
        if not any(issue.get("missing_result_report") for issue in no_report_synced.get("preflight_issues", [])):
            errors.append("missing result report evidence issue should be surfaced")

        md_only_state = Path(tmp) / "md-only-completed"
        md_only_state.mkdir()
        md_only_results = md_only_state / "results"
        md_only_results.mkdir()
        md_only_ownership = {
            "schema_version": 1,
            "task": "markdown-only completion evidence gate",
            "workspace_root": str(md_only_state),
            "tasks": [
                {
                    "task_id": "T011",
                    "session_name": "reviewer-md-only",
                    "role": "Reviewer",
                    "status": "completed",
                    "required_paths": ["adapters/openclaw/**"],
                    "result_report_json": str(md_only_results / "T011-reviewer-md-only.json"),
                    "result_report_markdown": str(md_only_results / "T011-reviewer-md-only.md"),
                }
            ],
        }
        write_json(md_only_state / "ownership.json", md_only_ownership)
        (md_only_results / "T011-reviewer-md-only.md").write_text(
            "\n".join(
                [
                    "task_id: T011",
                    "session_name: reviewer-md-only",
                    "role: Reviewer",
                    "status: completed",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        md_only_synced = sync_status(md_only_state)
        if md_only_synced["tasks"]["T011"]["status"] == "completed":
            errors.append("markdown-only completed task must not sync as completed without JSON report")
        if md_only_synced["gates"]["review_complete"]["status"] == "passed":
            errors.append("review gate must not pass with markdown-only result evidence")
        if not any(issue.get("missing_result_report") for issue in md_only_synced.get("preflight_issues", [])):
            errors.append("markdown-only missing JSON issue should be surfaced")

        merge_state = Path(tmp) / "merge-findings"
        merge_state.mkdir()
        (merge_state / "results").mkdir()
        (merge_state / "findings").mkdir()
        write_json(
            merge_state / "findings" / "review-findings.json",
            {
                "schema_version": 1,
                "findings": [
                    {
                        "source": "mcp",
                        "title": "MCP finding survives sync",
                        "severity": "P1",
                        "task_id": "T099",
                    }
                ],
            },
        )
        merge_ownership = {
            "schema_version": 1,
            "task": "merge findings",
            "workspace_root": str(merge_state),
            "tasks": [
                {
                    "task_id": "T003",
                    "session_name": "reviewer-merge",
                    "role": "Reviewer",
                    "status": "pending",
                    "required_paths": [],
                    "result_report_json": str(merge_state / "results" / "T003-reviewer-merge.json"),
                    "result_report_markdown": str(merge_state / "results" / "T003-reviewer-merge.md"),
                }
            ],
        }
        write_json(merge_state / "ownership.json", merge_ownership)
        sync_status(merge_state)
        merged_doc = read_json(merge_state / "findings" / "review-findings.json")
        titles = [item.get("title") for item in merged_doc.get("findings", [])]
        if "MCP finding survives sync" not in titles:
            errors.append("sync_status must merge MCP findings instead of clobbering")

        summary = summarize_run(state_dir, None)
        summary_text = Path(summary["summary_path"]).read_text(encoding="utf-8")
        if "Workspace / Preflight Issues" not in summary_text:
            errors.append("summary missing Workspace / Preflight Issues section")

        manual_bypass_state = Path(tmp) / "manual-completion-bypass"
        manual_bypass_state.mkdir()
        manual_results = manual_bypass_state / "results"
        manual_results.mkdir()
        manual_workspace = Path(tmp) / "manual-bypass-ws"
        manual_workspace.mkdir()
        manual_ownership = {
            "schema_version": 1,
            "task": "manual completion without result report (P1 regression)",
            "workspace_root": str(manual_workspace),
            "tasks": [
                {
                    "task_id": "T001",
                    "session_name": "explorer-no-report",
                    "role": "Explorer",
                    "mode": "research",
                    "runtime": "subagent",
                    "write_permission": False,
                    "allowed_paths": ["**/*"],
                    "blocked_paths": [".env"],
                    "result_report_json": str(manual_results / "T001-explorer-no-report.json"),
                    "result_report_markdown": str(manual_results / "T001-explorer-no-report.md"),
                    "status": "pending",
                }
            ],
        }
        write_json(manual_bypass_state / "ownership.json", manual_ownership)
        write_json(
            manual_bypass_state / "status.json",
            {"run_id": "MANUALP1", "gates": {}, "tasks": {}, "latest_audit": {}},
        )
        manual_updated = update_task(manual_bypass_state, "T001", "completed", None)
        manual_status = manual_updated["tasks"]["T001"]["status"]
        if manual_status != "blocked":
            errors.append(
                f"manual --status completed without result JSON must sync as blocked, got {manual_status!r}"
            )
        manual_preflight = manual_updated.get("preflight_issues", [])
        if not any(issue.get("missing_result_report") for issue in manual_preflight):
            errors.append("manual completion bypass must surface missing_result_report in preflight_issues")

        # --- auto-unblock: dependencies / blocked_by / ready_to_spawn (additive) ---
        au_state = Path(tmp) / "auto-unblock"
        au_state.mkdir()
        au_results = au_state / "results"
        au_results.mkdir()
        au_ownership = {
            "schema_version": 1,
            "task": "dependency auto-unblock",
            "workspace_root": str(au_state),
            "tasks": [
                {
                    "task_id": "T001",
                    "session_name": "explorer-backend",
                    "role": "Explorer",
                    "write_permission": False,
                    "allowed_paths": ["backend/**"],
                    "required_paths": [],
                    "dependencies": [],
                    "result_report_json": str(au_results / "T001-explorer-backend.json"),
                    "result_report_markdown": str(au_results / "T001-explorer-backend.md"),
                    "status": "pending",
                },
                {
                    "task_id": "T002",
                    "session_name": "worker-backend",
                    "role": "Worker",
                    "write_permission": True,
                    "allowed_paths": ["backend/**"],
                    "required_paths": [],
                    "dependencies": ["T001"],
                    "result_report_json": str(au_results / "T002-worker-backend.json"),
                    "result_report_markdown": str(au_results / "T002-worker-backend.md"),
                    "status": "pending",
                },
            ],
        }
        write_json(au_state / "ownership.json", au_ownership)
        au_sync = sync_status(au_state)
        t1 = au_sync["tasks"]["T001"]
        t2 = au_sync["tasks"]["T002"]
        if t1.get("ready_to_spawn") is not True or t1.get("blocked_by") != []:
            errors.append("auto-unblock: T001 (no deps) should be ready_to_spawn with empty blocked_by")
        if t2.get("ready_to_spawn") is not False or t2.get("blocked_by") != ["T001"]:
            errors.append("auto-unblock: T002 should be blocked_by [T001] and not ready while T001 pending")
        # Complete the dependency; T002 must auto-unblock.
        (au_results / "T001-explorer-backend.json").write_text(
            json.dumps({"task_id": "T001", "role": "Explorer", "status": "completed", "files_changed": []}),
            encoding="utf-8",
        )
        au_sync2 = sync_status(au_state)
        t2b = au_sync2["tasks"]["T002"]
        if t2b.get("blocked_by") != [] or t2b.get("ready_to_spawn") is not True:
            errors.append("auto-unblock: T002 should auto-unblock (ready_to_spawn) once T001 completes")
        if t2b.get("dependencies") != ["T001"]:
            errors.append("auto-unblock: dependencies should be echoed on the status entry")
        # readiness_report consumes the same signal for Main / loops.
        ready0 = readiness_report(au_sync)
        if ready0["ready"] != ["T001"] or ready0["blocked"].get("T002") != ["T001"]:
            errors.append(f"readiness_report initial wrong: {ready0}")
        ready1 = readiness_report(au_sync2)
        if "T002" not in ready1["ready"] or "T002" in ready1["blocked"]:
            errors.append(f"readiness_report after unblock wrong: {ready1}")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "update_task_status self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="Run built-in validation and exit")
    parser.add_argument("--state-dir", default=".codex-multi-agent", help="Mission control state directory")
    parser.add_argument("--sync", action="store_true", help="Rebuild status.json from ownership and result reports")
    parser.add_argument("--ready", action="store_true", help="Sync, then print tasks that are ready to spawn (dependency auto-unblock) and which are blocked")
    parser.add_argument("--summarize", action="store_true", help="Write run summary markdown for Main")
    parser.add_argument("--summary-out", help="Optional output path for --summarize")
    parser.add_argument("--task-id", help="Task id to update, e.g. T002")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES), help="New task status")
    parser.add_argument("--note", help="Optional note stored with the task status")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    state_dir = Path(args.state_dir)

    if args.task_id:
        if not args.status:
            parser.error("--status is required when --task-id is set")
        try:
            report = update_task(state_dir, args.task_id, args.status, args.note)
        except (FileNotFoundError, KeyError, ValueError) as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
            return 1
        print(json.dumps({"ok": True, "updated": args.task_id, "status": report}, indent=2))
        return 0

    if args.summarize:
        try:
            report = summarize_run(state_dir, Path(args.summary_out) if args.summary_out else None)
        except FileNotFoundError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
            return 1
        print(json.dumps(report, indent=2))
        if not report.get("ok"):
            if report.get("memory_update_error"):
                print(report["memory_update_error"], file=sys.stderr)
            return 1
        return 0

    if args.ready:
        try:
            report = sync_status(state_dir)
        except FileNotFoundError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
            return 1
        readiness = readiness_report(report)
        print(json.dumps({"ok": True, "current_phase": report.get("current_phase"), **readiness}, indent=2))
        return 0

    if args.sync:
        try:
            report = sync_status(state_dir)
        except FileNotFoundError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
            return 1
        print(json.dumps({"ok": True, "status": report}, indent=2))
        return 0

    parser.error("Specify --sync, --summarize, or --task-id with --status")


if __name__ == "__main__":
    raise SystemExit(main())
