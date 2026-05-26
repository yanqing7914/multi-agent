#!/usr/bin/env python3
"""Bridge MCP tools to v1 OpenClaw mission-control scripts (dependency-free)."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OPENCLAW_SCRIPTS = REPO_ROOT / "adapters" / "openclaw" / "scripts"
if str(OPENCLAW_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(OPENCLAW_SCRIPTS))

import audit_worker_output as audit_mod  # noqa: E402
import create_task_cards as ctc  # noqa: E402
import update_task_status as uts  # noqa: E402

SERVER_VERSION = "0.1.0"
DEFAULT_BLOCKED_PATHS = ctc.DEFAULT_BLOCKED_PATHS
DEFAULT_BLOCKED_COMMANDS = ctc.DEFAULT_BLOCKED_COMMANDS


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_state_dir(state_dir: str | Path | None, workspace: str | Path | None = None) -> Path:
    if state_dir:
        return Path(state_dir).expanduser().resolve()
    if workspace:
        return Path(workspace).expanduser().resolve() / ".codex-multi-agent"
    env = Path.cwd() / ".codex-multi-agent"
    return env.resolve()


def resolve_workspace_root(state_dir: Path, workspace: str | Path | None = None) -> Path:
    if workspace:
        return Path(workspace).expanduser().resolve()
    ownership = state_dir / "ownership.json"
    if ownership.exists():
        data = read_json(ownership)
        root = data.get("workspace_root") or data.get("target_repo")
        if root:
            return Path(root).expanduser().resolve()
    status = state_dir / "status.json"
    if status.exists():
        data = read_json(status)
        root = data.get("workspace_root") or data.get("target_repo")
        if root:
            return Path(root).expanduser().resolve()
    return Path.cwd().resolve()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def run_script(script: str, args: list[str]) -> tuple[int, dict | str]:
    cmd = [sys.executable, str(OPENCLAW_SCRIPTS / script), *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    text = (proc.stdout or proc.stderr or "").strip()
    try:
        payload = json.loads(text) if text else {}
    except json.JSONDecodeError:
        payload = text
    return proc.returncode, payload


def ensure_state_dirs(state_dir: Path) -> None:
    for name in ("tasks", "results", "findings", "approvals", "audits", "summary"):
        (state_dir / name).mkdir(parents=True, exist_ok=True)


def load_ownership(state_dir: Path) -> dict:
    path = state_dir / "ownership.json"
    if not path.exists():
        return {
            "schema_version": 1,
            "generated_at": utc_now(),
            "task": "",
            "state_dir": str(state_dir),
            "tasks": [],
        }
    return read_json(path)


def save_ownership(state_dir: Path, ownership: dict) -> None:
    ownership["updated_at"] = utc_now()
    write_json(state_dir / "ownership.json", ownership)


def task_dict_from_mcp(task: dict, workspace_root: Path) -> dict:
    role = task.get("role", "Worker")
    constraints = ctc.ROLE_CONSTRAINTS.get(role, ctc.ROLE_CONSTRAINTS["Worker"])
    session = task.get("session_name") or task.get("id", "task").lower().replace("_", "-")
    return {
        "task_id": task["id"],
        "session_name": session,
        "runtime": task.get("runtime", "native"),
        "mode": task.get("mode", "implement"),
        "role": role,
        "title": task.get("title", task["id"]),
        "objective": task.get("objective", ""),
        "allowed_paths": task.get("allowed_paths") or ["**/*"],
        "blocked_paths": task.get("forbidden_paths") or list(DEFAULT_BLOCKED_PATHS),
        "allowed_commands": task.get("allowed_commands") or ["rg", "find", "ls"],
        "blocked_commands": task.get("blocked_commands") or list(DEFAULT_BLOCKED_COMMANDS),
        "may_use_skills": task.get("may_use_skills") or [],
        "validation_required": task.get("validation_required") or [],
        "status": "pending",
        "target_repo": str(workspace_root),
        "dependencies": task.get("dependencies") or [],
    }


def create_task(state_dir: Path, workspace_root: Path, task: dict) -> dict:
    ensure_state_dirs(state_dir)
    internal = task_dict_from_mcp(task, workspace_root)
    ownership = load_ownership(state_dir)
    if not ownership.get("task"):
        ownership["task"] = internal.get("title", internal["task_id"])
    ownership["workspace_root"] = str(workspace_root)
    ownership["target_repo"] = str(workspace_root)
    ownership["state_dir"] = str(state_dir)
    ownership.setdefault("adapter_root", str(REPO_ROOT / "adapters" / "openclaw"))
    ownership.setdefault("adapter_scripts", {
        "create_task_cards": str(OPENCLAW_SCRIPTS / "create_task_cards.py"),
        "update_task_status": str(OPENCLAW_SCRIPTS / "update_task_status.py"),
        "audit_worker_output": str(OPENCLAW_SCRIPTS / "audit_worker_output.py"),
        "verify_workspace": str(OPENCLAW_SCRIPTS / "verify_workspace.py"),
    })

    tasks = ownership.setdefault("tasks", [])
    existing = {t["task_id"]: t for t in tasks}
    internal["required_paths"] = ctc.required_paths_for_task(internal, list(existing.values()) + [internal])
    paths = ctc.result_paths(state_dir, internal)
    constraints = ctc.ROLE_CONSTRAINTS.get(internal["role"], ctc.ROLE_CONSTRAINTS["Worker"])
    entry = {
        "task_id": internal["task_id"],
        "session_name": internal["session_name"],
        "role": internal["role"],
        "mode": internal["mode"],
        "runtime": internal["runtime"],
        "write_permission": constraints["write_permission"],
        "allowed_paths": internal["allowed_paths"],
        "required_paths": internal["required_paths"],
        "blocked_paths": internal["blocked_paths"],
        "result_report_json": paths["json"],
        "result_report_markdown": paths["markdown"],
        "status": "pending",
    }
    if internal["task_id"] in existing:
        idx = next(i for i, t in enumerate(tasks) if t["task_id"] == internal["task_id"])
        tasks[idx] = entry
    else:
        tasks.append(entry)

    all_tasks = [task_dict_from_mcp({"id": t["task_id"], **t}, workspace_root) if "id" not in t else t for t in tasks]
    all_internal = []
    for t in tasks:
        all_internal.append({
            "task_id": t["task_id"],
            "session_name": t["session_name"],
            "runtime": t.get("runtime", "native"),
            "mode": t.get("mode", "implement"),
            "role": t["role"],
            "title": t.get("title", t["task_id"]),
            "objective": t.get("objective", ""),
            "allowed_paths": t["allowed_paths"],
            "blocked_paths": t.get("blocked_paths", DEFAULT_BLOCKED_PATHS),
            "allowed_commands": t.get("allowed_commands", ["rg"]),
            "blocked_commands": t.get("blocked_commands", DEFAULT_BLOCKED_COMMANDS),
            "may_use_skills": t.get("may_use_skills", []),
            "validation_required": t.get("validation_required", []),
            "status": t.get("status", "pending"),
            "target_repo": str(workspace_root),
            "module": t.get("module"),
            "required_paths": t.get("required_paths") or [],
        })

    card_path = state_dir / "tasks" / f"{internal['task_id']}-{internal['session_name']}.md"
    ctc.write_card(card_path, internal, state_dir, all_internal, workspace_root)
    save_ownership(state_dir, ownership)

    if not (state_dir / "status.json").exists():
        ctc.write_status_json(state_dir, ownership.get("task", ""), all_internal, workspace_root)
        ctc.write_run_plan(state_dir, all_internal)
    else:
        uts.sync_status(state_dir)

    rel = card_path.relative_to(workspace_root) if card_path.is_relative_to(workspace_root) else card_path
    return {"ok": True, "task_id": internal["task_id"], "path": str(rel)}


def list_tasks(state_dir: Path, status: str = "any", role: str = "any") -> dict:
    ownership = load_ownership(state_dir)
    tasks = ownership.get("tasks", [])
    filtered = []
    for task in tasks:
        if status != "any" and task.get("status", "pending") != status:
            continue
        if role != "any" and task.get("role") != role:
            continue
        filtered.append(task)
    return {"ok": True, "tasks": filtered, "count": len(filtered)}


def get_task(state_dir: Path, task_id: str) -> dict:
    ownership = load_ownership(state_dir)
    for task in ownership.get("tasks", []):
        if task.get("task_id") == task_id:
            card = state_dir / "tasks" / f"{task_id}-{task['session_name']}.md"
            payload = {"ok": True, "task": task}
            if card.exists():
                payload["task_card_path"] = str(card)
                payload["task_card"] = card.read_text(encoding="utf-8")
            return payload
    return {"ok": False, "error": f"Task {task_id} not found"}


def update_task_status(state_dir: Path, task_id: str, status: str, note: str | None = None) -> dict:
    args = ["--state-dir", str(state_dir), "--task-id", task_id, "--status", status]
    if note:
        args.extend(["--note", note])
    code, payload = run_script("update_task_status.py", args)
    if code != 0:
        return {"ok": False, "error": payload}
    return {"ok": True, **payload} if isinstance(payload, dict) else {"ok": True, "result": payload}


def record_result(state_dir: Path, result: dict) -> dict:
    ensure_state_dirs(state_dir)
    task_id = result["task_id"]
    ownership = load_ownership(state_dir)
    matched = None
    for task in ownership.get("tasks", []):
        if task.get("task_id") == task_id:
            matched = task
            break
    if not matched:
        return {"ok": False, "error": f"Task {task_id} not found in ownership.json"}

    json_path = Path(matched.get("result_report_json", state_dir / "results" / f"{task_id}.json"))
    md_path = Path(matched.get("result_report_markdown", state_dir / "results" / f"{task_id}.md"))
    json_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(json_path, result)

    md_lines = [
        f"task_id: {result.get('task_id', task_id)}",
        f"session_name: {result.get('session_name', matched.get('session_name', ''))}",
        f"role: {result.get('role', matched.get('role', ''))}",
        f"status: {result.get('status', 'completed')}",
        f"summary: {result.get('summary', '')}",
    ]
    for key in ("files_read", "tools_used", "files_changed", "skills_used", "risks", "blockers"):
        items = result.get(key) or []
        md_lines.append(f"{key}:")
        if items:
            md_lines.extend(f"  - {item}" for item in items)
        else:
            md_lines.append("  []")
    md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    status = result.get("status", "completed")
    if status in uts.VALID_STATUSES:
        matched["status"] = status
        save_ownership(state_dir, ownership)

    synced = uts.sync_status(state_dir)
    return {
        "ok": True,
        "task_id": task_id,
        "result_json": str(json_path),
        "result_markdown": str(md_path),
        "sync": synced,
    }


def check_path_allowed(state_dir: Path, task_id: str, path: str, operation: str) -> dict:
    ownership = load_ownership(state_dir)
    task = next((t for t in ownership.get("tasks", []) if t.get("task_id") == task_id), None)
    if not task:
        return {"allowed": False, "reason": f"Task {task_id} not found"}

    normalized = audit_mod.normalize(path)
    blocked = list(dict.fromkeys(task.get("blocked_paths", []) + audit_mod.SECRET_PATTERNS))
    if audit_mod.matches(normalized, blocked):
        return {"allowed": False, "reason": "Path matches blocked/secret patterns"}

    role = task.get("role", "")
    write_permission = task.get("write_permission", role == "Worker")
    if operation == "write" and not write_permission:
        return {"allowed": False, "reason": f"Role {role} does not have write permission"}

    allowed = task.get("allowed_paths", [])
    if audit_mod.matches(normalized, allowed):
        return {"allowed": True, "reason": "Path matches allowed_paths."}
    return {"allowed": False, "reason": "Path is outside allowed_paths"}


def record_touched_paths(state_dir: Path, task_id: str, files_changed: list[str]) -> dict:
    ownership = load_ownership(state_dir)
    task = next((t for t in ownership.get("tasks", []) if t.get("task_id") == task_id), None)
    if not task:
        return {"ok": False, "error": f"Task {task_id} not found"}

    json_path = Path(task.get("result_report_json", ""))
    if json_path.exists():
        data = read_json(json_path)
    else:
        data = {
            "task_id": task_id,
            "session_name": task.get("session_name"),
            "role": task.get("role"),
            "status": task.get("status", "running"),
        }
    existing = data.get("files_changed") or []
    merged = list(dict.fromkeys([*existing, *[audit_mod.normalize(p) for p in files_changed]]))
    data["files_changed"] = merged
    write_json(json_path, data)
    return {"ok": True, "task_id": task_id, "files_changed": merged}


def next_request_id(state_dir: Path) -> str:
    approvals_dir = state_dir / "approvals"
    approvals_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(approvals_dir.glob("S*.json"))
    if not existing:
        return "S001"
    last = existing[-1].stem
    num = int(last[1:]) + 1 if last.startswith("S") and last[1:].isdigit() else len(existing) + 1
    return f"S{num:03d}"


def request_skill_use(
    state_dir: Path,
    task_id: str,
    requested_skill: str,
    reason: str,
    scope: list[str] | None = None,
    risk: str | None = None,
) -> dict:
    ensure_state_dirs(state_dir)
    request_id = next_request_id(state_dir)
    payload = {
        "schema_version": 1,
        "request_id": request_id,
        "task_id": task_id,
        "requested_skill": requested_skill,
        "reason": reason,
        "scope": scope or [],
        "risk": risk or "",
        "status": "pending",
        "created_at": utc_now(),
    }
    path = state_dir / "approvals" / f"{request_id}.json"
    write_json(path, payload)
    return {"ok": True, "request_id": request_id, "path": str(path)}


def approve_skill_use(
    state_dir: Path,
    request_id: str,
    approved: bool,
    approved_scope: list[str] | None = None,
    expires_after_task: bool = True,
) -> dict:
    path = state_dir / "approvals" / f"{request_id}.json"
    if not path.exists():
        return {"ok": False, "error": f"Approval request {request_id} not found"}
    payload = read_json(path)
    payload["status"] = "approved" if approved else "denied"
    payload["approved"] = approved
    payload["approved_scope"] = approved_scope or payload.get("scope", [])
    payload["expires_after_task"] = expires_after_task
    payload["decided_at"] = utc_now()
    write_json(path, payload)
    return {"ok": True, "request_id": request_id, "approved": approved, "path": str(path)}


def record_finding(state_dir: Path, finding: dict) -> dict:
    ensure_state_dirs(state_dir)
    findings_path = state_dir / "findings" / "review-findings.json"
    if findings_path.exists():
        doc = read_json(findings_path)
    else:
        doc = {"schema_version": 1, "findings": []}
    entry = dict(finding)
    entry.setdefault("status", "open")
    entry.setdefault("source", "mcp")
    doc.setdefault("findings", []).append(entry)
    doc["updated_at"] = utc_now()
    write_json(findings_path, doc)
    return {"ok": True, "finding_count": len(doc["findings"]), "path": str(findings_path)}


def list_framework_tools() -> dict:
    tools_dir = REPO_ROOT / "tools"
    entries = []
    if tools_dir.is_dir():
        for script in sorted(tools_dir.glob("*_tool.py")):
            entries.append(
                {
                    "name": script.stem,
                    "path": str(script.relative_to(REPO_ROOT)).replace("\\", "/"),
                    "cli_help": f"python3 {script.relative_to(REPO_ROOT)} --help",
                    "self_check": f"python3 {script.relative_to(REPO_ROOT)} --self-check",
                }
            )
    return {"ok": True, "tools": entries, "count": len(entries), "directory": str(tools_dir.relative_to(REPO_ROOT))}


def _finding_dedup_key(item: dict) -> tuple:
    title = item.get("title") or item.get("raw") or json.dumps(item, sort_keys=True)
    return (
        title,
        item.get("task_id") or item.get("reviewer_task_id"),
        item.get("severity", "P2"),
        item.get("source", ""),
    )


def _finding_content_hash(item: dict) -> str:
    import hashlib

    payload = json.dumps(item, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _dedupe_findings(findings: list[dict], group_duplicates: bool = True) -> list[dict]:
    if not group_duplicates:
        return list(findings)

    seen_keys: dict[tuple, dict] = {}
    seen_hashes: set[str] = set()
    grouped: list[dict] = []

    for item in findings:
        content_hash = _finding_content_hash(item)
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)

        key = _finding_dedup_key(item)
        if key in seen_keys:
            seen_keys[key]["count"] = seen_keys[key].get("count", 1) + 1
            continue

        copy = dict(item)
        copy["count"] = 1
        seen_keys[key] = copy
        grouped.append(copy)

    return grouped


def summarize_review(state_dir: Path, include_resolved: bool = False, group_duplicates: bool = True) -> dict:
    findings_path = state_dir / "findings" / "review-findings.json"
    if not findings_path.exists():
        return {"ok": True, "findings": [], "finding_count": 0, "summary": "No findings recorded"}

    doc = read_json(findings_path)
    findings = doc.get("findings", [])
    if not include_resolved:
        findings = [f for f in findings if f.get("status", "open") != "resolved"]
    findings = _dedupe_findings(findings, group_duplicates=group_duplicates)

    by_severity: dict[str, list] = {}
    for item in findings:
        sev = item.get("severity", "P2")
        by_severity.setdefault(sev, []).append(item)

    return {
        "ok": True,
        "finding_count": len(findings),
        "by_severity": {k: len(v) for k, v in sorted(by_severity.items())},
        "findings": findings,
        "path": str(findings_path),
    }


def audit_scope(state_dir: Path) -> dict:
    ownership_path = state_dir / "ownership.json"
    if not ownership_path.exists():
        return {"ok": False, "error": "ownership.json not found"}
    changed = state_dir / "changed-files.txt"
    args = [
        "--ownership", str(ownership_path),
        "--results", str(state_dir / "results"),
        "--write-audit",
        "--state-dir", str(state_dir),
    ]
    if changed.exists():
        args.extend(["--changed-files", str(changed)])
    code, payload = run_script("audit_worker_output.py", args)
    if isinstance(payload, dict):
        uts.sync_status(state_dir)
        return {"ok": payload.get("ok", code == 0), **payload}
    return {"ok": code == 0, "result": payload}


def generate_final_report(
    state_dir: Path,
    include_tasks: bool = True,
    include_findings: bool = True,
    include_validation: bool = True,
) -> dict:
    code, payload = run_script("update_task_status.py", ["--state-dir", str(state_dir), "--summarize"])
    if code != 0:
        return {"ok": False, "error": payload}

    report: dict = {"ok": True}
    if isinstance(payload, dict):
        report.update(payload)

    summary_path = state_dir / "summary" / "run-summary.md"
    if summary_path.exists():
        report["summary_text"] = summary_path.read_text(encoding="utf-8")

    status_doc = read_json(state_dir / "status.json") if (state_dir / "status.json").exists() else {}
    ownership = load_ownership(state_dir)

    sections: dict = {}
    if include_tasks:
        sections["tasks"] = ownership.get("tasks", [])
        sections["gates"] = status_doc.get("gates", {})
    if include_findings:
        fp = state_dir / "findings" / "review-findings.json"
        sections["findings"] = read_json(fp).get("findings", []) if fp.exists() else []
    if include_validation:
        sections["preflight_issues"] = status_doc.get("preflight_issues", [])
        sections["latest_audit"] = status_doc.get("latest_audit", {})

    report["report"] = sections
    return report


def read_resource(uri: str, state_dir: Path) -> tuple[str, str]:
    """Return (mime_type, text) for MCP resource read."""
    mapping = {
        "multi-agent://state": (state_dir / "status.json", "application/json"),
        "multi-agent://tasks": (state_dir / "tasks", "application/json"),
        "multi-agent://findings": (state_dir / "findings" / "review-findings.json", "application/json"),
        "multi-agent://approvals": (state_dir / "approvals", "application/json"),
    }
    if uri not in mapping:
        raise FileNotFoundError(f"Unknown resource: {uri}")
    path, mime = mapping[uri]
    if path.is_dir():
        entries = sorted(p.name for p in path.iterdir())
        return mime, json.dumps({"path": str(path), "entries": entries}, indent=2)
    if not path.exists():
        return mime, json.dumps({"path": str(path), "exists": False}, indent=2)
    return mime, path.read_text(encoding="utf-8")
