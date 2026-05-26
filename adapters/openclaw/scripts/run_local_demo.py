#!/usr/bin/env python3
"""
Deterministic local demo for OpenClaw v1 mission control (no real agent spawns).

Generates task cards, simulates result reports, runs sync/audit/summary, and
proves gates block false completion, thin evidence, and workspace mismatch.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent

from _runtimes import DEMO_SPAWN_RUNTIME  # noqa: E402


def run_cmd(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def write_result(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def demo_run(state_dir: Path, workspace_root: Path, keep: bool = False) -> dict:
    """Execute full demo; return structured outcome."""
    steps: list[dict] = []
    errors: list[str] = []

    create = SCRIPT_DIR / "create_task_cards.py"
    status_py = SCRIPT_DIR / "update_task_status.py"
    audit_py = SCRIPT_DIR / "audit_worker_output.py"
    example_yaml = SCRIPT_DIR.parent / "examples" / "dogfood-openclaw.yaml"

    if state_dir.exists():
        shutil.rmtree(state_dir)
    state_dir.mkdir(parents=True)

    proc = run_cmd(
        [
            sys.executable,
            str(create),
            "--from-yaml",
            str(example_yaml),
            "--out",
            str(state_dir),
            "--workspace-root",
            str(workspace_root),
        ],
        cwd=REPO_ROOT,
    )
    steps.append({"step": "create_task_cards", "returncode": proc.returncode})
    if proc.returncode != 0:
        errors.append(f"create_task_cards failed: {proc.stderr or proc.stdout}")
        return {"ok": False, "errors": errors, "steps": steps}

    ownership = load_json(state_dir / "ownership.json")
    if ownership.get("workspace_root") != str(workspace_root):
        errors.append("ownership.json workspace_root does not match --workspace-root")
    explorer = next(
        (t for t in ownership["tasks"] if t.get("role") == "Explorer" and "openclaw" in t.get("session_name", "")),
        None,
    )
    if explorer and explorer.get("allowed_paths") != ["adapters/openclaw/**"]:
        errors.append(f"openclaw_adapter path map wrong: {explorer.get('allowed_paths')}")

    card_path = state_dir / "tasks" / f"{explorer['task_id']}-{explorer['session_name']}.md" if explorer else None
    if card_path and card_path.exists():
        card_text = card_path.read_text(encoding="utf-8")
        for needle in ("workspace_root:", "target_repo:", "preflight_command:", 'verify_workspace.py"'):
            if needle not in card_text:
                errors.append(f"task card missing {needle}")

    tasks_by_role: dict[str, list] = {}
    for t in ownership["tasks"]:
        tasks_by_role.setdefault(t["role"], []).append(t)

    root_str = str(workspace_root)
    adapter_files = [
        "adapters/openclaw/SKILL.md",
        "adapters/openclaw/README.md",
        "adapters/openclaw/scripts/create_task_cards.py",
    ]

    for task in tasks_by_role.get("Explorer", []):
        write_result(
            Path(task["result_report_json"]),
            {
                "task_id": task["task_id"],
                "session_name": task["session_name"],
                "role": "Explorer",
                "status": "completed",
                "workspace_observed": root_str,
                "required_paths_checked": task.get("required_paths", []),
                "required_paths_missing": [],
                "required_paths_verified": True,
                "files_read": adapter_files[:2],
                "files_changed": [],
                "summary": "Explorer demo: adapter layout confirmed",
            },
        )

    for task in tasks_by_role.get("Reviewer", []):
        write_result(
            Path(task["result_report_json"]),
            {
                "task_id": task["task_id"],
                "session_name": task["session_name"],
                "role": "Reviewer",
                "status": "completed",
                "workspace_observed": root_str,
                "required_paths_checked": task.get("required_paths", []),
                "required_paths_missing": [],
                "required_paths_verified": True,
                "files_read": adapter_files,
                "files_changed": [],
                "findings": [{"severity": "P3", "title": "Demo finding — no issues"}],
                "summary": "Reviewer demo with evidence",
            },
        )

    if tasks_by_role.get("Verifier"):
        v = tasks_by_role["Verifier"][0]
        write_result(
            Path(v["result_report_json"]),
            {
                "task_id": v["task_id"],
                "session_name": v["session_name"],
                "role": "Verifier",
                "status": "completed",
                "workspace_observed": root_str,
                "required_paths_verified": True,
                "files_read": adapter_files,
                "files_changed": [],
                "commands_run": [f"{sys.executable} adapters/openclaw/scripts/create_task_cards.py --self-check"],
                "summary": "Verifier demo passed self-check command",
            },
        )

    proc = run_cmd([sys.executable, str(status_py), "--state-dir", str(state_dir), "--sync"])
    steps.append({"step": "sync_valid_reports", "returncode": proc.returncode})
    status_valid = load_json(state_dir / "status.json")
    if status_valid.get("gates", {}).get("explorers_complete", {}).get("status") != "passed":
        errors.append("explorers_complete should pass after valid Explorer reports")
    if status_valid.get("gates", {}).get("review_complete", {}).get("status") != "passed":
        errors.append("review_complete should pass after valid Reviewer reports")

    worker = next((t for t in ownership["tasks"] if t["role"] == "Worker"), None)
    if worker:
        write_result(
            Path(worker["result_report_json"]),
            {
                "task_id": worker["task_id"],
                "session_name": worker["session_name"],
                "role": "Worker",
                "status": "completed",
                "workspace_observed": root_str,
                "required_paths_verified": True,
                "files_read": ["adapters/openclaw/scripts/run_local_demo.py"],
                "files_changed": ["adapters/openclaw/scripts/run_local_demo.py"],
                "summary": "Worker demo scope",
            },
        )
        changed_list = state_dir / "changed-files.txt"
        changed_list.write_text("adapters/openclaw/scripts/run_local_demo.py\n", encoding="utf-8")
        proc = run_cmd(
            [
                sys.executable,
                str(audit_py),
                "--ownership",
                str(state_dir / "ownership.json"),
                "--results",
                str(state_dir / "results"),
                "--changed-files",
                str(changed_list),
                "--write-audit",
                "--state-dir",
                str(state_dir),
            ]
        )
        steps.append({"step": "audit_worker", "returncode": proc.returncode})
        audit_out = json.loads(proc.stdout) if proc.stdout.strip() else {}
        if not audit_out.get("ok"):
            errors.append(f"worker audit should pass before false reports: {proc.stdout}")
        proc = run_cmd([sys.executable, str(status_py), "--state-dir", str(state_dir), "--sync"])
        steps.append({"step": "sync_after_worker_audit", "returncode": proc.returncode})
        status_worker = load_json(state_dir / "status.json")
        if status_worker.get("gates", {}).get("scope_audit", {}).get("status") != "passed":
            errors.append("scope_audit gate should pass after Worker audit")
        if status_worker.get("latest_audit", {}).get("ok") is not True:
            errors.append("latest_audit.ok must be true only when scope_audit gate passed")
        if status_worker.get("gates", {}).get("workers_complete", {}).get("status") != "passed":
            errors.append("workers_complete should pass after Worker report")

        changed_list.write_text(
            "adapters/openclaw/scripts/run_local_demo.py\nadapters/openclaw/README.md\n",
            encoding="utf-8",
        )
        proc = run_cmd([sys.executable, str(status_py), "--state-dir", str(state_dir), "--sync"])
        steps.append({"step": "sync_stale_changed_files", "returncode": proc.returncode})
        status_stale = load_json(state_dir / "status.json")
        if status_stale.get("gates", {}).get("scope_audit", {}).get("status") != "pending":
            errors.append("scope_audit must be pending when changed-files.txt changes after audit")
        if not status_stale.get("latest_audit", {}).get("stale"):
            errors.append("latest_audit.stale must be set after changed-files drift")
    else:
        errors.append("dogfood yaml should include a Worker (mode: implement)")

    false_task = {
        "task_id": "T999",
        "session_name": "reviewer-false-demo",
        "role": "Reviewer",
        "mode": "review",
        "runtime": DEMO_SPAWN_RUNTIME,
        "write_permission": False,
        "allowed_paths": ["**/*"],
        "required_paths": ["adapters/openclaw/**"],
        "blocked_paths": [".env"],
        "result_report_json": str(state_dir / "results" / "T999-reviewer-false-demo.json"),
        "result_report_markdown": str(state_dir / "results" / "T999-reviewer-false-demo.md"),
        "status": "pending",
    }
    ownership["tasks"].append(false_task)
    (state_dir / "ownership.json").write_text(json.dumps(ownership, indent=2) + "\n", encoding="utf-8")
    write_result(
        Path(false_task["result_report_json"]),
        {
            "task_id": "T999",
            "session_name": "reviewer-false-demo",
            "role": "Reviewer",
            "status": "completed",
            "workspace_observed": "/tmp/wrong-workspace",
            "required_paths_verified": False,
            "required_paths_missing": ["adapters/openclaw/**"],
            "files_read": [],
            "files_changed": [],
            "summary": "Simulated wrong workspace false completion",
        },
    )

    proc = run_cmd([sys.executable, str(status_py), "--state-dir", str(state_dir), "--sync"])
    steps.append({"step": "sync_false_completion", "returncode": proc.returncode})
    status_false = load_json(state_dir / "status.json")
    if status_false.get("tasks", {}).get("T999", {}).get("status") != "blocked":
        errors.append("false completion report must sync as blocked")
    if not status_false.get("preflight_issues"):
        errors.append("preflight_issues must list false completion")
    false_reasons = [i.get("reason", "") for i in status_false.get("preflight_issues", [])]
    if not any("required_paths_verified=false" in r or "workspace_mismatch" in r for r in false_reasons):
        errors.append("preflight_issues should cite false completion or workspace mismatch")

    thin_task = {
        "task_id": "T998",
        "session_name": "reviewer-thin-demo",
        "role": "Reviewer",
        "mode": "review",
        "runtime": DEMO_SPAWN_RUNTIME,
        "write_permission": False,
        "allowed_paths": ["**/*"],
        "required_paths": ["adapters/openclaw/**"],
        "blocked_paths": [".env"],
        "result_report_json": str(state_dir / "results" / "T998-reviewer-thin-demo.json"),
        "result_report_markdown": str(state_dir / "results" / "T998-reviewer-thin-demo.md"),
        "status": "pending",
    }
    ownership["tasks"].append(thin_task)
    (state_dir / "ownership.json").write_text(json.dumps(ownership, indent=2) + "\n", encoding="utf-8")
    write_result(
        Path(thin_task["result_report_json"]),
        {
            "task_id": "T998",
            "session_name": "reviewer-thin-demo",
            "role": "Reviewer",
            "status": "completed",
            "workspace_observed": root_str,
            "required_paths_verified": True,
            "required_paths_missing": [],
            "files_read": [],
            "files_changed": [],
            "summary": "Simulated thin evidence (empty files_read)",
        },
    )
    proc = run_cmd([sys.executable, str(status_py), "--state-dir", str(state_dir), "--sync"])
    steps.append({"step": "sync_thin_evidence", "returncode": proc.returncode})
    status_thin = load_json(state_dir / "status.json")
    if status_thin.get("tasks", {}).get("T998", {}).get("status") != "blocked":
        errors.append("thin evidence report must sync as blocked")

    proc = run_cmd([sys.executable, str(status_py), "--state-dir", str(state_dir), "--sync"])
    steps.append({"step": "sync_after_false_reports", "returncode": proc.returncode})

    proc = run_cmd([sys.executable, str(status_py), "--state-dir", str(state_dir), "--summarize"])
    steps.append({"step": "summarize", "returncode": proc.returncode})
    summary_path = state_dir / "summary" / "run-summary.md"
    if not summary_path.exists():
        errors.append("run-summary.md not created")
    else:
        text = summary_path.read_text(encoding="utf-8")
        if "Workspace / Preflight Issues" not in text:
            errors.append("summary missing preflight section")
        if "T999" not in text:
            errors.append("summary should mention false-completion task T999")

    non_worker = next((t for t in ownership["tasks"] if t["role"] == "Reviewer" and t["task_id"] not in {"T999", "T998"}), None)
    if non_worker:
        data = load_json(Path(non_worker["result_report_json"]))
        data["files_changed"] = ["adapters/openclaw/SKILL.md"]
        write_result(Path(non_worker["result_report_json"]), data)
        proc = run_cmd(
            [
                sys.executable,
                str(audit_py),
                "--ownership",
                str(state_dir / "ownership.json"),
                "--results",
                str(state_dir / "results"),
            ]
        )
        audit_bad = json.loads(proc.stdout) if proc.stdout.strip() else {}
        if audit_bad.get("ok"):
            errors.append("audit should fail when Reviewer reports files_changed")
        steps.append({"step": "audit_non_worker_changed", "ok": not audit_bad.get("ok")})

    missing_worker_errors = demo_missing_worker_report()
    if missing_worker_errors:
        errors.extend(missing_worker_errors)
        steps.append({"step": "missing_worker_report", "ok": False})
    else:
        steps.append({"step": "missing_worker_report", "ok": True})

    return {
        "ok": not errors,
        "errors": errors,
        "steps": steps,
        "state_dir": str(state_dir),
        "workspace_root": str(workspace_root),
        "final_phase": load_json(state_dir / "status.json").get("current_phase") if (state_dir / "status.json").exists() else None,
    }


def demo_missing_worker_report() -> list[str]:
    """Isolated check: strict audit warns when a Worker report is missing."""
    errors: list[str] = []
    audit_py = SCRIPT_DIR / "audit_worker_output.py"
    with tempfile.TemporaryDirectory(prefix="openclaw-missing-worker-") as tmp:
        root = Path(tmp)
        ownership = {
            "schema_version": 1,
            "workspace_root": str(REPO_ROOT),
            "tasks": [
                {
                    "task_id": "T001",
                    "session_name": "worker-only",
                    "role": "Worker",
                    "allowed_paths": ["backend/**"],
                    "blocked_paths": [".env"],
                    "status": "pending",
                }
            ],
        }
        ownership_path = root / "ownership.json"
        ownership_path.write_text(json.dumps(ownership, indent=2), encoding="utf-8")
        results_dir = root / "results"
        results_dir.mkdir()
        proc = run_cmd(
            [
                sys.executable,
                str(audit_py),
                "--ownership",
                str(ownership_path),
                "--results",
                str(results_dir),
                "--strict",
            ]
        )
        if proc.returncode == 0:
            errors.append("strict audit should fail when Worker result report is missing")
        report = json.loads(proc.stdout) if proc.stdout.strip() else {}
        if not any(item.get("reason") == "Worker result report not found" for item in report.get("violations", [])):
            errors.append("expected Worker result report not found violation in strict mode")
    return errors


def run_self_check() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="openclaw-demo-") as tmp:
        state_dir = Path(tmp) / ".codex-multi-agent"
        outcome = demo_run(state_dir, REPO_ROOT.resolve(), keep=True)
        if not outcome["ok"]:
            errors.extend(outcome["errors"])

    scripts = [
        SCRIPT_DIR / "create_task_cards.py",
        SCRIPT_DIR / "update_task_status.py",
        SCRIPT_DIR / "audit_worker_output.py",
        SCRIPT_DIR / "verify_workspace.py",
    ]
    for script in scripts:
        proc = run_cmd([sys.executable, str(script), "--self-check"])
        if proc.returncode != 0:
            errors.append(f"{script.name} --self-check failed: {proc.stderr or proc.stdout}")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "run_local_demo self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="Run demo in temp dir + all script self-checks")
    parser.add_argument(
        "--out",
        help="State directory for demo artifacts (default: system temp dir outside adapter package)",
    )
    parser.add_argument("--workspace-root", help="Target repo root (default: repo root)")
    parser.add_argument("--keep", action="store_true", help="Keep state dir after run (for inspection)")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    workspace_root = Path(args.workspace_root).resolve() if args.workspace_root else REPO_ROOT.resolve()
    temp_state: tempfile.TemporaryDirectory[str] | None = None
    if args.out:
        state_dir = Path(args.out)
        if state_dir.exists():
            shutil.rmtree(state_dir)
    else:
        temp_state = tempfile.TemporaryDirectory(prefix="openclaw-demo-", dir=None)
        state_dir = Path(temp_state.name) / ".codex-multi-agent"

    exit_code = 1
    try:
        outcome = demo_run(state_dir, workspace_root, keep=args.keep)
        print(json.dumps(outcome, indent=2))
        exit_code = 0 if outcome["ok"] else 1
    finally:
        if not args.keep:
            if temp_state is not None:
                temp_state.cleanup()
            elif args.out and Path(args.out).exists():
                shutil.rmtree(args.out, ignore_errors=True)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
