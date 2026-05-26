#!/usr/bin/env python3
"""Guarded Claude Code dogfood: skip cleanly on quota/429 (dependency-free)."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent.parent / "_shared"
OPENCLAW = Path(__file__).resolve().parent.parent.parent / "openclaw" / "scripts"
sys.path.insert(0, str(SHARED))

from bridge import parse_task_card, run_preflight, workspace_root_from_card  # noqa: E402
from worker_outcome import detect_log_error_mode, evaluate_worker_outcome, shell_with_pipefail  # noqa: E402

FIXTURE_429 = SHARED / "fixtures" / "claude_429_budget.log"
LAUNCHER = Path(__file__).resolve().parent / "launch_claude_worker.py"


def budget_skip_payload(task_card: Path, workspace_root: Path, log_text: str, details: dict | None = None) -> dict:
    return {
        "ok": True,
        "status": "skipped",
        "reason": "budget exceeded",
        "message": "skipped: budget exceeded",
        "runtime": "claude-code",
        "mode": "local",
        "task_card": str(task_card),
        "workspace_root": str(workspace_root),
        "log_error_mode": detect_log_error_mode(log_text),
        **(details or {}),
    }


def run_fixture_self_check() -> int:
    log_text = FIXTURE_429.read_text(encoding="utf-8")
    mode = detect_log_error_mode(log_text)
    if mode != "quota_exhausted":
        print(json.dumps({"ok": False, "error": f"fixture expected quota_exhausted, got {mode}"}))
        return 1
    payload = budget_skip_payload(Path("fixture-task-card.md"), Path.cwd(), log_text, {"self_check": True})
    if payload.get("status") != "skipped":
        print(json.dumps({"ok": False, "error": "expected skipped status"}))
        return 1
    print(json.dumps({"ok": True, "message": "dogfood_claude 429 fixture reports skipped", "payload": payload}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-card", help="Path to .codex-multi-agent/tasks/*.md")
    parser.add_argument("--state-dir", help="Mission-control dir")
    parser.add_argument("--mode", choices=("local", "acp"), default="local")
    parser.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    parser.add_argument("--fixture-log", help="Simulate launcher log (self-check); skips external CLI")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check or args.fixture_log:
        if args.fixture_log:
            log_text = Path(args.fixture_log).read_text(encoding="utf-8")
            if detect_log_error_mode(log_text):
                print(json.dumps(budget_skip_payload(Path("fixture.md"), Path.cwd(), log_text), indent=2))
                return 0
            print(json.dumps({"ok": False, "error": "fixture log did not match budget pattern"}))
            return 1
        return run_fixture_self_check()

    if not args.task_card:
        parser.error("--task-card is required unless --self-check or --fixture-log")

    task_card_path = Path(args.task_card).expanduser().resolve()
    if not task_card_path.is_file():
        print(json.dumps({"ok": False, "error": f"task card not found: {task_card_path}"}))
        return 1

    state_dir = Path(args.state_dir).resolve() if args.state_dir else task_card_path.parent.parent
    card = parse_task_card(task_card_path)
    workspace_root = workspace_root_from_card(card, state_dir)

    required_paths = [str(p) for p in card.get("required_paths", [])]
    preflight_code, preflight_payload = run_preflight(workspace_root, required_paths)
    if preflight_code != 0:
        print(json.dumps({"ok": False, "stage": "preflight", **preflight_payload}, indent=2))
        return preflight_code or 2

    if args.mode == "acp":
        proc = subprocess.run(
            [sys.executable, str(LAUNCHER), "--task-card", str(task_card_path), "--mode", "acp"],
            capture_output=True,
            text=True,
            check=False,
        )
        print(proc.stdout or proc.stderr)
        return proc.returncode

    result_md = Path(card.get("result_markdown_path") or state_dir / "results" / f"{task_card_path.stem}.md")
    result_json = Path(card.get("result_json_path") or result_md.with_suffix(".json"))
    result_md.parent.mkdir(parents=True, exist_ok=True)

    from bridge import build_worker_prompt  # noqa: E402

    prompt = build_worker_prompt(task_card_path, card, workspace_root)
    shell = shell_with_pipefail(
        f"cd {shlex.quote(str(workspace_root))} && "
        f"{shlex.quote(args.claude_bin)} --print --permission-mode bypassPermissions "
        f"{shlex.quote(prompt)} 2>&1 | tee {shlex.quote(str(result_md))}"
    )
    proc = subprocess.run(["bash", "-lc", shell], check=False)
    log_text = result_md.read_text(encoding="utf-8") if result_md.exists() else ""

    if detect_log_error_mode(log_text):
        payload = budget_skip_payload(
            task_card_path,
            workspace_root,
            log_text,
            {
                "returncode": proc.returncode,
                "result_markdown": str(result_md),
                "result_json": str(result_json),
            },
        )
        print(json.dumps(payload, indent=2))
        return 0

    from bridge import try_extract_json_from_log  # noqa: E402

    extracted = try_extract_json_from_log(log_text, result_json)
    ok, error, outcome_details = evaluate_worker_outcome(
        pipeline_returncode=proc.returncode,
        result_md=result_md,
        result_json=result_json,
        json_extracted=extracted,
        log_text=log_text,
    )
    payload = {
        "ok": ok,
        "status": "ok" if ok else "failed",
        "runtime": "claude-code",
        "mode": "local",
        "workspace_root": str(workspace_root),
        "task_card": str(task_card_path),
        "result_markdown": str(result_md),
        "result_json": str(result_json),
        "returncode": proc.returncode,
        **outcome_details,
    }
    if error:
        payload["error"] = error
    print(json.dumps(payload, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
