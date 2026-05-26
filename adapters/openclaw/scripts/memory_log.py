#!/usr/bin/env python3
"""Persistent memory log for multi-agent runs (dependency-free)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def resolve_workspace_root(state_dir: Path) -> Path:
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
    return state_dir.parent.resolve()


def memory_dir(state_dir: Path) -> Path:
    path = state_dir / "memory"
    path.mkdir(parents=True, exist_ok=True)
    return path


def memory_md_path(workspace_root: Path) -> Path:
    return workspace_root / "MEMORY.md"


def append_memory_line(workspace_root: Path, line: str) -> Path:
    path = memory_md_path(workspace_root)
    if not path.exists():
        path.write_text(
            "# Project Memory\n\n"
            "Append-only log of multi-agent decisions and run outcomes.\n"
            "Do not store secrets, credentials, or tokens here.\n\n",
            encoding="utf-8",
        )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip() + "\n")
    return path


def append_freeform(state_dir: Path, line: str) -> dict:
    workspace_root = resolve_workspace_root(state_dir)
    run_id = "manual"
    status_path = state_dir / "status.json"
    if status_path.exists():
        run_id = read_json(status_path).get("run_id", run_id)
    run_file = memory_dir(state_dir) / f"run-{run_id}.md"
    if not run_file.exists():
        run_file.write_text(f"# Run memory: {run_id}\n\n", encoding="utf-8")
    timestamp = utc_now()
    run_file.write_text(run_file.read_text(encoding="utf-8") + f"- [{timestamp}] {line}\n", encoding="utf-8")
    one_liner = f"- [{timestamp}] {line}"
    memory_path = append_memory_line(workspace_root, one_liner)
    return {"ok": True, "run_file": str(run_file), "memory_md": str(memory_path), "line": one_liner}


def gate_summary(gates: dict) -> str:
    parts = []
    for name, gate in gates.items():
        parts.append(f"{name}={gate.get('status', 'pending')}")
    return ", ".join(parts)


def from_run(state_dir: Path) -> dict:
    status_path = state_dir / "status.json"
    if not status_path.exists():
        return {"ok": False, "error": "status.json not found"}

    status_doc = read_json(status_path)
    ownership = read_json(state_dir / "ownership.json") if (state_dir / "ownership.json").exists() else {}
    workspace_root = resolve_workspace_root(state_dir)
    run_id = status_doc.get("run_id", datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    task_title = ownership.get("task") or status_doc.get("task_title") or "untitled run"

    findings_count = 0
    findings_path = state_dir / "findings" / "review-findings.json"
    if findings_path.exists():
        findings_count = len(read_json(findings_path).get("findings", []))

    audit_ok = status_doc.get("latest_audit", {}).get("ok")
    audit_gate = status_doc.get("latest_audit", {}).get("gate_status", "pending")
    gates = gate_summary(status_doc.get("gates", {}))

    summary_path = state_dir / "summary" / "run-summary.md"
    key_findings = []
    if summary_path.exists():
        mini = summary_path.read_text(encoding="utf-8")
        for line in mini.splitlines():
            if line.startswith("- [P"):
                key_findings.append(line.strip().lstrip("- "))
            if len(key_findings) >= 3:
                break

    run_file = memory_dir(state_dir) / f"run-{run_id}.md"
    lines = [
        f"# Run memory: {run_id}",
        "",
        f"- Task: {task_title}",
        f"- Run ID: {run_id}",
        f"- Gates: {gates}",
        f"- Audit: ok={audit_ok} gate={audit_gate}",
        f"- Findings count: {findings_count}",
    ]
    if key_findings:
        lines.append("- Key findings:")
        lines.extend(f"  - {item}" for item in key_findings)
    lines.append("")
    run_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    one_liner = (
        f"- [{utc_now()}] run {run_id}: {task_title} | gates: {gates} | audit={audit_gate} | findings={findings_count}"
    )
    memory_path = append_memory_line(workspace_root, one_liner)
    return {
        "ok": True,
        "run_id": run_id,
        "run_file": str(run_file),
        "memory_md": str(memory_path),
        "one_liner": one_liner,
    }


def tail_memory(workspace_root: Path, lines: int = 8) -> str:
    path = memory_md_path(workspace_root)
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8").splitlines()
    tail = [line for line in content if line.strip() and not line.startswith("#")][-lines:]
    if not tail:
        return ""
    return "Recent project memory:\n" + "\n".join(tail)


def run_self_check() -> int:
    import tempfile

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="memory-log-") as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir()
        state_dir = workspace / ".codex-multi-agent"
        state_dir.mkdir()
        (state_dir / "ownership.json").write_text(
            json.dumps({"task": "Self-check", "workspace_root": str(workspace)}),
            encoding="utf-8",
        )
        (state_dir / "status.json").write_text(
            json.dumps(
                {
                    "run_id": "TEST001",
                    "gates": {"explorers_complete": {"status": "passed"}},
                    "latest_audit": {"ok": True, "gate_status": "passed"},
                }
            ),
            encoding="utf-8",
        )
        (state_dir / "findings").mkdir()
        (state_dir / "findings" / "review-findings.json").write_text(
            json.dumps({"findings": [{"title": "sample"}]}),
            encoding="utf-8",
        )
        (state_dir / "summary").mkdir()
        (state_dir / "summary" / "run-summary.md").write_text(
            "# Summary\n\n## Review Findings\n\n- [P1] sample finding\n",
            encoding="utf-8",
        )

        appended = append_freeform(state_dir, "decision: use stdlib-only tools")
        if not appended.get("ok"):
            errors.append("append_freeform failed")
        if not (workspace / "MEMORY.md").exists():
            errors.append("MEMORY.md not created")

        logged = from_run(state_dir)
        if not logged.get("ok"):
            errors.append("from_run failed")
        tail = tail_memory(workspace)
        if "run TEST001" not in tail and "decision" not in tail:
            errors.append("tail_memory missing expected content")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "memory_log self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=".codex-multi-agent", help="Mission-control state directory")
    parser.add_argument("--append", help="Append a freeform decision/event line")
    parser.add_argument("--from-run", action="store_true", help="Append memory from last status.json + summary")
    parser.add_argument("--tail", type=int, help="Print MEMORY.md tail for workspace (lines)")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    state_dir = Path(args.state_dir).expanduser().resolve()
    if args.from_run:
        print(json.dumps(from_run(state_dir), indent=2))
        return 0

    if args.append:
        print(json.dumps(append_freeform(state_dir, args.append), indent=2))
        return 0

    if args.tail is not None:
        workspace = resolve_workspace_root(state_dir)
        print(tail_memory(workspace, args.tail))
        return 0

    parser.error("Specify --append, --from-run, --tail, or --self-check")


if __name__ == "__main__":
    raise SystemExit(main())
