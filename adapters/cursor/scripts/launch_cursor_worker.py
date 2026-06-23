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
import time
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

COMPLETED_STATUSES = {"completed", "blocked"}
FOREGROUND_TIMEOUT_SECONDS = 300


def _run_id() -> str:
    raw = os.environ.get("RUN_ID") or time.strftime("%Y%m%d%H%M%S")
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in raw).strip("-")
    return f"{safe}-{os.getpid()}" if safe else str(os.getpid())


def _is_completed_report(result_json: Path) -> bool:
    if not result_json.is_file():
        return False
    try:
        payload = json.loads(result_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return payload.get("status") in COMPLETED_STATUSES


def _capture_tmux(session: str) -> str:
    proc = subprocess.run(
        ["tmux", "capture-pane", "-p", "-S", "-2000", "-t", session],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout or proc.stderr or ""


def _write_timeout_marker(state_dir: Path, task_id: str, session: str) -> Path:
    marker = state_dir / "results" / f"{task_id}-cursor-launcher-timeout.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        "\n".join(
            [
                "Cursor launcher timed out waiting for worker result JSON.",
                f"tmux_session: {session}",
                "",
                "--- tmux capture-pane ---",
                _capture_tmux(session).rstrip(),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return marker


def _ensure_markdown_companion(result_md: Path, result_json: Path) -> bool:
    if result_md.is_file() and result_md.stat().st_size >= 64:
        return False
    try:
        payload = json.loads(result_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    status = payload.get("status")
    if status not in COMPLETED_STATUSES:
        return False
    files_changed = payload.get("files_changed") or []
    tools_used = payload.get("tools_used") or []
    lines = [
        f"task_id: {payload.get('task_id', 'unknown')}",
        "role: Worker",
        f"status: {status}",
        f"summary: {payload.get('summary', 'Cursor worker wrote JSON result only')}",
        "",
        "launcher_note: Cursor CLI did not leave a Markdown companion; generated from completed JSON.",
        "",
        "tools_used:",
        *[f"  - {item}" for item in tools_used],
        "",
        "files_changed:",
        *[f"  - {item}" for item in files_changed],
    ]
    result_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def _wait_for_completed_report(result_md: Path, result_json: Path, timeout_seconds: int) -> bool:
    deadline = time.monotonic() + timeout_seconds
    delay = 1.0
    while time.monotonic() < deadline:
        if _is_completed_report(result_json):
            return True
        if result_md.exists():
            log_text = result_md.read_text(encoding="utf-8", errors="replace")
            try_extract_json_from_log(log_text, result_json)
            if _is_completed_report(result_json):
                return True
        time.sleep(delay)
        delay = min(delay * 1.5, 10.0)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-card", required=True, help="Path to .codex-multi-agent/tasks/*.md")
    parser.add_argument("--state-dir", help="Mission-control dir (default: parent of tasks/)")
    parser.add_argument("--session", help="tmux session name override")
    parser.add_argument("--foreground", action="store_true", help="Wait for tmux worker result before returning")
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
    launcher_log = result_md.with_name(f"{result_md.stem}-cursor-launcher.log")
    result_md.parent.mkdir(parents=True, exist_ok=True)

    task_id = card.get("task_id", task_card_path.stem.split("-")[0])
    session = args.session or f"cursor-{task_id}-{_run_id()}"

    if args.foreground:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".md") as tmp:
            tmp.write(prompt)
            prompt_file = tmp.name
        shell = shell_with_pipefail(
            f"cd {shlex.quote(str(workspace_root))} && "
            f'cursor_bin="$(command -v agent || command -v cursor-agent || echo agent)" && '
            f'"$cursor_bin" -p {shlex.quote(Path(prompt_file).read_text(encoding="utf-8"))} '
            f"--force --trust --output-format text 2>&1 | tee {shlex.quote(str(launcher_log))}"
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
                        "hint": "Install tmux and ensure the Cursor CLI (`agent` or legacy `cursor-agent`) is on PATH",
                    },
                    indent=2,
                )
            )
            return proc.returncode or 1
        completed = _wait_for_completed_report(result_md, result_json, FOREGROUND_TIMEOUT_SECONDS)
        if not completed:
            marker = _write_timeout_marker(state_dir, str(task_id), session)
            print(
                json.dumps(
                    {
                        "ok": False,
                        "runtime": "cursor",
                        "mode": "tmux-foreground",
                        "stage": "timeout",
                        "tmux_session": session,
                        "timeout_seconds": FOREGROUND_TIMEOUT_SECONDS,
                        "timeout_marker": str(marker),
                    },
                    indent=2,
                )
            )
            return 124
        markdown_companion_generated = _ensure_markdown_companion(result_md, result_json)
        log_text = launcher_log.read_text(encoding="utf-8") if launcher_log.exists() else ""
        extracted = try_extract_json_from_log(log_text, result_json)
        ok, error, outcome_details = evaluate_worker_outcome(
            pipeline_returncode=0,
            result_md=result_md,
            result_json=result_json,
            json_extracted=extracted,
            log_text=log_text,
            runtime="cursor",
        )
        payload = {
            "ok": ok,
            "runtime": "cursor",
            "mode": "tmux-foreground",
            "tmux_session": session,
            "workspace_root": str(workspace_root),
            "result_markdown": str(result_md),
            "result_json": str(result_json),
            "launcher_log": str(launcher_log),
            "json_extracted": extracted,
            "markdown_companion_generated": markdown_companion_generated,
            "returncode": 0,
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
        f'cursor_bin="$(command -v agent || command -v cursor-agent || echo agent)" && '
        f'"$cursor_bin" -p {shlex.quote(open(prompt_file, encoding="utf-8").read())} '
        f"--force --trust --output-format text 2>&1 | tee {shlex.quote(str(launcher_log))}"
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
                    "hint": "Install tmux and ensure the Cursor CLI (`agent` or legacy `cursor-agent`) is on PATH",
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
        "launcher_log": str(launcher_log),
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
