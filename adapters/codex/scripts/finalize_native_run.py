#!/usr/bin/env python3
"""Finalize a Codex native multi-agent run before Main delivers."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
UPDATE_TASK_STATUS = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "update_task_status.py"
AUDIT_WORKER_OUTPUT = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "audit_worker_output.py"
CREATE_TASK_CARDS = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "create_task_cards.py"
PREPARE_NATIVE_PLAN = SCRIPT_DIR / "prepare_native_plan.py"


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, cwd=str(cwd) if cwd else None)


def load_plan(plan_json: Path | None, state_dir: Path) -> dict:
    if plan_json and plan_json.is_file():
        return json.loads(plan_json.read_text(encoding="utf-8"))
    proc = run([sys.executable, str(PREPARE_NATIVE_PLAN), "--state-dir", str(state_dir)])
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr or proc.stdout, "records": []}
    return json.loads(proc.stdout)


def report_checks(records: list[dict]) -> list[dict]:
    checks: list[dict] = []
    for record in records:
        task_id = record.get("task_id")
        json_path = Path(record.get("result_json") or "")
        md_path = Path(record.get("result_markdown") or "")
        errors: list[str] = []
        payload: dict = {}
        if not json_path.is_file():
            errors.append(f"missing JSON report: {json_path}")
        else:
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON report: {exc}")
        if not md_path.is_file():
            errors.append(f"missing Markdown report: {md_path}")
        if payload:
            if payload.get("task_id") != task_id:
                errors.append(f"JSON task_id mismatch: {payload.get('task_id')} != {task_id}")
            if payload.get("status") not in {"completed", "blocked", "failed"}:
                errors.append(f"invalid status: {payload.get('status')}")
            if payload.get("status") == "completed" and payload.get("required_paths_verified") is not True:
                errors.append("completed report must set required_paths_verified=true")
        checks.append(
            {
                "task_id": task_id,
                "role": record.get("role"),
                "ok": not errors,
                "result_json": str(json_path),
                "result_markdown": str(md_path),
                "errors": errors,
            }
        )
    return checks


def write_changed_files(state_dir: Path, workspace_root: Path) -> Path:
    """Capture staged + unstaged + untracked changes via the shared helper.

    Plain `git diff --name-only` misses untracked files, which would let new
    files created outside allowed_paths escape the scope audit.
    """
    changed_path = state_dir / "changed-files.txt"
    capture_script = REPO_ROOT / "adapters" / "openclaw" / "scripts" / "capture_changed_files.py"
    proc = run(
        [
            sys.executable,
            str(capture_script),
            "--workspace-root",
            str(workspace_root),
            "--state-dir",
            str(state_dir),
        ],
        cwd=workspace_root,
    )
    if proc.returncode != 0 or not changed_path.exists():
        changed_path.write_text("", encoding="utf-8")
    return changed_path


def finalize(state_dir: Path, workspace_root: Path, plan_json: Path | None, skip_audit: bool) -> dict:
    plan = load_plan(plan_json, state_dir)
    records = plan.get("records", [])
    reports = report_checks(records)
    errors = [f"{item['task_id']}: {err}" for item in reports for err in item["errors"]]

    sync_payload: dict = {"skipped": True}
    sync = run([sys.executable, str(UPDATE_TASK_STATUS), "--state-dir", str(state_dir), "--sync"])
    if sync.returncode == 0 and sync.stdout.strip():
        try:
            sync_payload = json.loads(sync.stdout)
        except json.JSONDecodeError:
            sync_payload = {"ok": True, "stdout": sync.stdout.strip()}
    else:
        errors.append(f"gate sync failed: {sync.stderr or sync.stdout}")
        sync_payload = {"ok": False, "output": sync.stderr or sync.stdout}

    changed_files = write_changed_files(state_dir, workspace_root)
    audit_payload: dict = {"skipped": skip_audit}
    if not skip_audit:
        audit = run(
            [
                sys.executable,
                str(AUDIT_WORKER_OUTPUT),
                "--ownership",
                str(state_dir / "ownership.json"),
                "--results",
                str(state_dir / "results"),
                "--changed-files",
                str(changed_files),
                "--write-audit",
                "--state-dir",
                str(state_dir),
            ],
            cwd=workspace_root,
        )
        if audit.returncode == 0 and audit.stdout.strip():
            try:
                audit_payload = json.loads(audit.stdout)
            except json.JSONDecodeError:
                audit_payload = {"ok": False, "output": audit.stdout}
                errors.append("scope audit output was not JSON")
        else:
            audit_payload = {"ok": False, "output": audit.stderr or audit.stdout}
            errors.append(f"scope audit failed: {audit.stderr or audit.stdout}")
        if audit_payload.get("ok") is not True:
            errors.append("scope audit did not pass")

    return {
        "ok": not errors,
        "state_dir": str(state_dir),
        "workspace_root": str(workspace_root),
        "records_count": len(records),
        "report_checks": reports,
        "changed_files": str(changed_files),
        "gate_sync": sync_payload,
        "scope_audit": audit_payload,
        "errors": errors,
        "final_delivery_allowed": not errors,
    }


def run_self_check() -> int:
    with tempfile.TemporaryDirectory(prefix="codex-finalize-native-") as tmp:
        tmp_path = Path(tmp)
        state_dir = tmp_path / ".codex-multi-agent"
        create = run(
            [
                sys.executable,
                str(CREATE_TASK_CARDS),
                "--task",
                "Finalize native self-check",
                "--mode",
                "review",
                "--modules",
                "docs",
                "--runtime",
                "codex",
                "--workspace-root",
                str(REPO_ROOT),
                "--out",
                str(state_dir),
            ]
        )
        if create.returncode != 0:
            print(json.dumps({"ok": False, "stage": "create_task_cards", "output": create.stderr or create.stdout}, indent=2))
            return 1
        plan = load_plan(None, state_dir)
        result_dir = state_dir / "results"
        result_dir.mkdir(exist_ok=True)
        for record in plan.get("records", []):
            payload = {
                "task_id": record["task_id"],
                "session_name": record["session_name"],
                "role": record["role"],
                "status": "completed",
                "workspace_observed": str(REPO_ROOT),
                "required_paths_checked": ["docs/**"],
                "required_paths_missing": [],
                "required_paths_verified": True,
                "files_read": ["README.md"],
                "tools_used": ["repo_index_tool"],
                "files_changed": [],
            }
            Path(record["result_json"]).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            Path(record["result_markdown"]).write_text(f"# {record['task_id']} result\nstatus: completed\n", encoding="utf-8")
        payload = finalize(state_dir, REPO_ROOT, None, skip_audit=True)
        if not payload["ok"]:
            print(json.dumps({"ok": False, "stage": "finalize", "payload": payload}, indent=2))
            return 1
        print(json.dumps({"ok": True, "adapter": "codex-finalize-native", "records": payload["records_count"]}, indent=2))
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=".codex-multi-agent")
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--plan-json", help="Optional saved JSON output from prepare_native_plan.py")
    parser.add_argument("--skip-audit", action="store_true", help="Skip scope audit (self-check/demo only)")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    payload = finalize(
        Path(args.state_dir).expanduser().resolve(),
        Path(args.workspace_root).expanduser().resolve(),
        Path(args.plan_json).expanduser().resolve() if args.plan_json else None,
        args.skip_audit,
    )
    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
