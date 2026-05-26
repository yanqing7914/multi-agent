#!/usr/bin/env python3
"""Launch a Cursor worker via tmux + agent CLI (dependency-free)."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent.parent / "_shared"
sys.path.insert(0, str(SHARED))

from bridge import (  # noqa: E402
    build_worker_prompt,
    parse_task_card,
    run_preflight,
    try_extract_json_from_log,
    workspace_root_from_card,
)
from worker_outcome import evaluate_worker_outcome, shell_with_pipefail  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-card", required=True, help="Path to .codex-multi-agent/tasks/*.md")
    parser.add_argument("--state-dir", help="Mission-control dir (default: parent of tasks/)")
    parser.add_argument("--session", help="tmux session name override")
    parser.add_argument("--foreground", action="store_true", help="Run agent in foreground (no tmux)")
    args = parser.parse_args()

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

    prompt = build_worker_prompt(task_card_path, card, workspace_root)
    result_md = Path(card.get("result_markdown_path") or state_dir / "results" / f"{task_card_path.stem}.md")
    result_json = Path(card.get("result_json_path") or result_md.with_suffix(".json"))
    result_md.parent.mkdir(parents=True, exist_ok=True)

    task_id = card.get("task_id", task_card_path.stem.split("-")[0])
    session = args.session or f"cursor-{task_id}"

    if args.foreground:
        shell = shell_with_pipefail(
            f"cd {shlex.quote(str(workspace_root))} && "
            f"agent -p {shlex.quote(prompt)} --force --trust --output-format text "
            f"2>&1 | tee {shlex.quote(str(result_md))}"
        )
        proc = subprocess.run(["bash", "-lc", shell], check=False)
        log_text = result_md.read_text(encoding="utf-8") if result_md.exists() else ""
        extracted = try_extract_json_from_log(log_text, result_json)
        ok, error, outcome_details = evaluate_worker_outcome(
            pipeline_returncode=proc.returncode,
            result_md=result_md,
            result_json=result_json,
            json_extracted=extracted,
            log_text=log_text,
            runtime="cursor",
        )
        payload = {
            "ok": ok,
            "runtime": "cursor",
            "mode": "foreground",
            "workspace_root": str(workspace_root),
            "result_markdown": str(result_md),
            "result_json": str(result_json),
            "json_extracted": extracted,
            "returncode": proc.returncode,
            **outcome_details,
        }
        if error:
            payload["error"] = error
        print(json.dumps(payload, indent=2))
        return 0 if ok else 1

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as tmp:
        tmp.write(prompt)
        prompt_file = tmp.name

    shell = shell_with_pipefail(
        f"cd {shlex.quote(str(workspace_root))} && "
        f"agent -p {shlex.quote(open(prompt_file, encoding='utf-8').read())} "
        f"--force --trust --output-format text 2>&1 | tee {shlex.quote(str(result_md))}"
    )
    tmux_cmd = ["tmux", "new-session", "-d", "-s", session, "bash", "-lc", shell]
    proc = subprocess.run(tmux_cmd, capture_output=True, text=True, check=False)
    os.unlink(prompt_file)

    if proc.returncode != 0:
        print(
            json.dumps(
                {
                    "ok": False,
                    "stage": "tmux",
                    "stderr": (proc.stderr or proc.stdout or "").strip(),
                    "hint": "Install tmux and ensure `agent` CLI is on PATH",
                },
                indent=2,
            )
        )
        return proc.returncode or 1

    payload = {
        "ok": True,
        "runtime": "cursor",
        "mode": "tmux",
        "tmux_session": session,
        "workspace_root": str(workspace_root),
        "task_card": str(task_card_path),
        "result_markdown": str(result_md),
        "result_json": str(result_json),
        "attach": f"tmux attach -t {session}",
        "caveat": (
            "tmux mode returns after spawn only; Main must poll result files and run "
            "evaluate_worker_outcome-equivalent checks before marking workers_complete. "
            "Use --foreground for synchronous validation."
        ),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
