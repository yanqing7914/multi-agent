#!/usr/bin/env python3
"""Build Cursor SDK / headless-CLI run specs from ownership.json (dependency-free).

This is the *native* Cursor orchestration path that complements the deterministic
`agent` CLI bridge (`launch_cursor_worker.py`). It reads the mission-control
`ownership.json`, selects every write-permission Worker, and emits:

  (a) a single JSON run-spec consumed by `adapters/cursor/sdk/run_workers.mjs`
      (the `@cursor/sdk` reference launcher), and
  (b) one copy-paste headless command per Worker:
        agent -p @<prompt-file> --force --output-format json   (cwd = workspace_root)

It NEVER runs `agent` or `npm`; the default behaviour is dry: it only writes the
run-spec, writes one prompt file per Worker, and (optionally) prints the commands.
Worker prompts reuse `adapters/_shared/bridge.py:build_worker_prompt` when a task
card is present so the allowed_paths + dual result-report contract is preserved;
otherwise it falls back to an ownership-only prompt that states the same contract.
"""

from __future__ import annotations

import argparse
import json
import shlex
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Reuse the shared bridge prompt builder when importable (see launch_cursor_worker.py).
SHARED = Path(__file__).resolve().parent.parent.parent / "_shared"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

try:  # bridge is stdlib-only; failure just means we use the fallback prompt.
    from bridge import build_worker_prompt, parse_task_card  # noqa: E402

    _BRIDGE_AVAILABLE = True
except Exception:  # pragma: no cover - defensive: keep working without _shared
    _BRIDGE_AVAILABLE = False

RESULT_REPORT_SCHEMA = "adapters/openclaw/templates/result-report.md"
READ_ONLY_ROLES = {"Explorer", "Reviewer", "Verifier"}
SDK_RUNTIME_ENV = "CURSOR_SDK_RUNTIME"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_stem(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in (value or "")).strip("-")
    return safe or "worker"


def _truthy(value: object) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() == "true")


def is_writer_worker(task: object) -> bool:
    """A Worker that may edit files: role == Worker and write_permission is true."""
    if not isinstance(task, dict):
        return False
    if task.get("role") != "Worker":
        return False
    if task.get("role") in READ_ONLY_ROLES:
        return False
    # write_permission is authoritative; default to True only when the key is absent
    # (older ownership files), never when it is explicitly false.
    return _truthy(task.get("write_permission", True))


def load_ownership(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("ownership.json must be a JSON object")
    return data


def fallback_prompt(task: dict, workspace_root: Path) -> str:
    """Ownership-only prompt used when no task card exists for the Worker."""
    allowed = task.get("allowed_paths") or ["(none listed - stop and ask)"]
    allowed_block = "\n".join(f"  - {item}" for item in allowed)
    json_path = task.get("result_report_json", "")
    md_path = task.get("result_report_markdown", "")
    return (
        "You are a scoped Cursor Worker in a multi-agent coding workflow.\n"
        "Other agents may be editing disjoint scopes; never revert or overwrite work you did not make.\n\n"
        f"task_id: {task.get('task_id', '')}\n"
        f"session_name: {task.get('session_name', '')}\n"
        "role: Worker\n"
        f"workspace_root: {workspace_root}\n\n"
        "MANDATORY FIRST STEPS (do not skip):\n"
        f"  cd {workspace_root}\n"
        "  pwd\n\n"
        "SCOPE (hard boundary):\n"
        "  Edit ONLY within allowed_paths:\n"
        f"{allowed_block}\n"
        "  Do not touch secrets/blocked paths, install dependencies, deploy, push, or expand scope.\n"
        "  If you must edit outside allowed_paths, stop and report status=blocked instead.\n\n"
        "RESULT REPORT CONTRACT (write BOTH files before claiming completion):\n"
        f"  JSON: {json_path}\n"
        f"  Markdown: {md_path}\n"
        f"  Use the schema in {RESULT_REPORT_SCHEMA}.\n"
        "  Set workspace_observed to pwd after cd; list every file opened in files_read and every tool in tools_used.\n"
        "  If required paths are missing, set status=blocked and required_paths_verified=false; do not fake completion.\n"
    )


def worker_prompt(task: dict, state_dir: Path, workspace_root: Path) -> tuple[str, str]:
    """Return (prompt_text, prompt_source). Prefer bridge.build_worker_prompt."""
    card_path = state_dir / "tasks" / f"{task.get('task_id', '')}-{task.get('session_name', '')}.md"
    if _BRIDGE_AVAILABLE and card_path.is_file():
        try:
            card = parse_task_card(card_path)
            return build_worker_prompt(card_path, card, workspace_root), "bridge.build_worker_prompt"
        except Exception:
            # Fall through to the ownership-only prompt on any parse/build error.
            pass
    return fallback_prompt(task, workspace_root), "fallback"


def headless_command(prompt_path: Path) -> str:
    """One-line Cursor headless invocation; cwd is applied by the caller/runnable line."""
    prompt_ref = shlex.quote("@" + str(prompt_path))
    return f"agent -p {prompt_ref} --force --output-format json"


def runnable_line(entry: dict) -> str:
    """Copy-paste POSIX line that sets cwd and runs the headless command."""
    return f"cd {shlex.quote(entry['cwd'])} && {entry['headless_command']}"


def build_worker_entry(
    task: dict,
    state_dir: Path,
    workspace_root: Path,
    prompts_dir: Path,
    write_prompts: bool,
) -> dict:
    prompt, source = worker_prompt(task, state_dir, workspace_root)
    task_id = task.get("task_id", "")
    session_name = task.get("session_name", "")
    stem = _safe_stem(f"{task_id}-{session_name}" if session_name else task_id)
    prompt_path = prompts_dir / f"{stem}.md"
    if write_prompts:
        prompts_dir.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(prompt, encoding="utf-8")
    return {
        "task_id": task_id,
        "session_name": session_name,
        "role": task.get("role", "Worker"),
        "workspace_root": str(workspace_root),
        "cwd": str(workspace_root),
        "allowed_paths": list(task.get("allowed_paths") or []),
        "result_report_paths": {
            "json": task.get("result_report_json", ""),
            "markdown": task.get("result_report_markdown", ""),
        },
        "prompt_path": str(prompt_path),
        "prompt": prompt,
        "prompt_source": source,
        "headless_command": headless_command(prompt_path),
        "sdk_runtime_default": "local",
    }


def build_run_spec(
    ownership: dict,
    ownership_path: Path,
    state_dir: Path,
    out_path: Path,
    write_prompts: bool = True,
) -> dict:
    workspace_root = Path(
        str(ownership.get("workspace_root") or ownership.get("target_repo") or state_dir.parent)
    )
    prompts_dir = out_path.parent / "prompts"
    workers = [
        build_worker_entry(task, state_dir, workspace_root, prompts_dir, write_prompts)
        for task in ownership.get("tasks", [])
        if is_writer_worker(task)
    ]
    return {
        "schema_version": 1,
        "generated_at": _utc_now(),
        "adapter": "cursor",
        "runtime_path": "cursor-sdk",
        "ownership": str(ownership_path),
        "state_dir": str(state_dir),
        "workspace_root": str(workspace_root),
        "result_report_schema": RESULT_REPORT_SCHEMA,
        "sdk_runtime_default": "local",
        "sdk_runtime_env": SDK_RUNTIME_ENV,
        "sdk_launcher": "adapters/cursor/sdk/run_workers.mjs",
        "headless_note": (
            "Each worker headless_command is dry until you run it; set cwd to the "
            "worker's workspace_root (the runnable line below does this with cd)."
        ),
        "worker_count": len(workers),
        "workers": workers,
    }


def write_run_spec(spec: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")


def print_commands(spec: dict, out_path: Path) -> None:
    """Emit copy-paste / bash-pipeable headless commands (comments start with #)."""
    lines = [
        "# Cursor headless Worker commands (multi-agent-coding cursor-sdk path)",
        f"# run-spec: {out_path}",
        f"# workspace_root: {spec.get('workspace_root', '')}",
        "# Dry until executed. Each line cd's to workspace_root, then runs the Cursor agent.",
    ]
    if not spec.get("workers"):
        lines.append("# (no write-permission Workers found in ownership.json)")
    for worker in spec.get("workers", []):
        report = worker.get("result_report_paths", {})
        lines.append(
            f"# {worker.get('task_id')} {worker.get('session_name')} "
            f"-> json:{report.get('json', '')}"
        )
        lines.append(runnable_line(worker))
    print("\n".join(lines))


def _build_self_check_ownership(state_dir: Path, workspace_root: Path) -> dict:
    """Minimal ownership.json: 1 Explorer + 2 Worker + 1 Reviewer."""
    results = state_dir / "results"

    def report(stem: str, ext: str) -> str:
        return str(results / f"{stem}.{ext}")

    tasks = [
        {
            "task_id": "T001",
            "session_name": "explorer-backend",
            "role": "Explorer",
            "write_permission": False,
            "allowed_paths": ["backend/**"],
            "result_report_json": report("T001-explorer-backend", "json"),
            "result_report_markdown": report("T001-explorer-backend", "md"),
        },
        {
            "task_id": "T002",
            "session_name": "worker-backend",
            "role": "Worker",
            "write_permission": True,
            "allowed_paths": ["backend/**", "api/**"],
            "result_report_json": report("T002-worker-backend", "json"),
            "result_report_markdown": report("T002-worker-backend", "md"),
        },
        {
            "task_id": "T003",
            "session_name": "worker-frontend",
            "role": "Worker",
            "write_permission": True,
            "allowed_paths": ["frontend/**", "src/**"],
            "result_report_json": report("T003-worker-frontend", "json"),
            "result_report_markdown": report("T003-worker-frontend", "md"),
        },
        {
            "task_id": "T004",
            "session_name": "reviewer-correctness",
            "role": "Reviewer",
            "write_permission": False,
            "allowed_paths": ["**/*"],
            "result_report_json": report("T004-reviewer-correctness", "json"),
            "result_report_markdown": report("T004-reviewer-correctness", "md"),
        },
    ]
    return {
        "schema_version": 1,
        "workspace_root": str(workspace_root),
        "target_repo": str(workspace_root),
        "state_dir": str(state_dir),
        "tasks": tasks,
    }


def _write_self_check_card(state_dir: Path, workspace_root: Path) -> None:
    """Write a parse-able task card for T002 to exercise the bridge prompt path."""
    results = state_dir / "results"
    card = "\n".join(
        [
            "task_id: T002",
            "session_name: worker-backend",
            "role: Worker",
            f"workspace_root: {workspace_root}",
            f"target_repo: {workspace_root}",
            "preflight_command:",
            f'  - cd "{workspace_root}"',
            "  - pwd",
            "allowed_paths:",
            "  - backend/**",
            "  - api/**",
            "result_report_paths:",
            f"  json: {results / 'T002-worker-backend.json'}",
            f"  markdown: {results / 'T002-worker-backend.md'}",
            "",
        ]
    )
    (state_dir / "tasks" / "T002-worker-backend.md").write_text(card, encoding="utf-8")


def run_self_check() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="cursor-sdk-selfcheck-") as tmp:
        tmp_path = Path(tmp)
        state_dir = tmp_path / ".codex-multi-agent"
        (state_dir / "tasks").mkdir(parents=True)
        (state_dir / "results").mkdir(parents=True)
        workspace_root = tmp_path / "repo"
        workspace_root.mkdir()

        ownership = _build_self_check_ownership(state_dir, workspace_root)
        ownership_path = state_dir / "ownership.json"
        ownership_path.write_text(json.dumps(ownership, indent=2), encoding="utf-8")
        # T002 gets a real card (bridge path); T003 stays card-less (fallback path).
        _write_self_check_card(state_dir, workspace_root)

        out_path = state_dir / "cursor-sdk" / "run-spec.json"
        spec = build_run_spec(ownership, ownership_path, state_dir, out_path, write_prompts=True)
        write_run_spec(spec, out_path)
        workers = spec["workers"]

        # 1. exactly the 2 write-permission Workers, no Explorer/Reviewer.
        if spec["worker_count"] != 2 or len(workers) != 2:
            errors.append(f"expected 2 Worker specs, got {spec.get('worker_count')}")
        ids = sorted(w["task_id"] for w in workers)
        if ids != ["T002", "T003"]:
            errors.append(f"expected only Worker ids T002,T003; got {ids}")
        if any(w["role"] != "Worker" for w in workers):
            errors.append("non-Worker role leaked into run spec")

        # 2. fields complete + headless json flag + report contract.
        required_fields = (
            "task_id",
            "session_name",
            "workspace_root",
            "cwd",
            "allowed_paths",
            "result_report_paths",
            "prompt",
            "prompt_path",
            "prompt_source",
            "headless_command",
        )
        for worker in workers:
            for key in required_fields:
                if not worker.get(key):
                    errors.append(f"{worker.get('task_id')} missing field {key}")
            command = worker.get("headless_command", "")
            if "--output-format json" not in command:
                errors.append(f"{worker.get('task_id')} headless command missing --output-format json")
            if "agent -p" not in command:
                errors.append(f"{worker.get('task_id')} headless command missing 'agent -p'")
            if "--force" not in command:
                errors.append(f"{worker.get('task_id')} headless command missing --force")
            report = worker.get("result_report_paths") or {}
            if not report.get("json") or not report.get("markdown"):
                errors.append(f"{worker.get('task_id')} result_report_paths incomplete")
            if not worker.get("allowed_paths"):
                errors.append(f"{worker.get('task_id')} allowed_paths empty")
            if not Path(worker.get("prompt_path", "")).is_file():
                errors.append(f"{worker.get('task_id')} prompt file not written")
            prompt = worker.get("prompt", "")
            if report.get("json", "") and report["json"] not in prompt:
                errors.append(f"{worker.get('task_id')} prompt missing result JSON path contract")
            if "result report" not in prompt.lower():
                errors.append(f"{worker.get('task_id')} prompt missing result-report contract language")
            line = runnable_line(worker)
            if "agent -p" not in line or "--output-format json" not in line:
                errors.append(f"{worker.get('task_id')} runnable line malformed")

        # 3. both prompt sources exercised.
        by_id = {w["task_id"]: w for w in workers}
        if _BRIDGE_AVAILABLE and by_id.get("T002", {}).get("prompt_source") != "bridge.build_worker_prompt":
            errors.append("T002 should use bridge.build_worker_prompt when its task card exists")
        if by_id.get("T003", {}).get("prompt_source") != "fallback":
            errors.append("T003 should use the fallback prompt (no task card)")

        # 4. run-spec written and round-trips.
        if not out_path.is_file():
            errors.append("run-spec.json not written")
        else:
            try:
                reloaded = json.loads(out_path.read_text(encoding="utf-8"))
                if reloaded.get("worker_count") != 2:
                    errors.append("run-spec.json worker_count mismatch after reload")
                if reloaded.get("sdk_launcher") != "adapters/cursor/sdk/run_workers.mjs":
                    errors.append("run-spec.json missing sdk_launcher pointer")
            except json.JSONDecodeError as exc:
                errors.append(f"run-spec.json invalid: {exc}")

        # 5. read-only roles are filtered by the predicate too.
        if is_writer_worker(ownership["tasks"][0]) or is_writer_worker(ownership["tasks"][3]):
            errors.append("is_writer_worker should reject Explorer/Reviewer")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "adapter": "cursor-sdk",
                "message": "prepare_cursor_sdk self-check passed",
                "workers": 2,
                "bridge_prompt_available": _BRIDGE_AVAILABLE,
            },
            indent=2,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--ownership",
        default=".codex-multi-agent/ownership.json",
        help="Path to mission-control ownership.json (default: .codex-multi-agent/ownership.json)",
    )
    parser.add_argument(
        "--out",
        help="Where to write the run-spec JSON (default: <state_dir>/cursor-sdk/run-spec.json)",
    )
    parser.add_argument(
        "--print-commands",
        action="store_true",
        help="Print copy-paste headless commands instead of the JSON summary (still writes run-spec)",
    )
    parser.add_argument("--self-check", action="store_true", help="Run built-in validation and exit")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    ownership_path = Path(args.ownership).expanduser().resolve()
    if not ownership_path.is_file():
        print(json.dumps({"ok": False, "error": f"ownership.json not found: {ownership_path}"}, indent=2))
        return 1
    try:
        ownership = load_ownership(ownership_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": f"invalid ownership.json: {exc}"}, indent=2))
        return 1

    state_dir = ownership_path.parent
    out_path = (
        Path(args.out).expanduser().resolve()
        if args.out
        else state_dir / "cursor-sdk" / "run-spec.json"
    )

    spec = build_run_spec(ownership, ownership_path, state_dir, out_path, write_prompts=True)
    write_run_spec(spec, out_path)

    if args.print_commands:
        print_commands(spec, out_path)
        return 0

    summary = {
        "ok": True,
        "adapter": "cursor",
        "runtime_path": "cursor-sdk",
        "run_spec": str(out_path),
        "prompts_dir": str(out_path.parent / "prompts"),
        "workspace_root": spec["workspace_root"],
        "worker_count": spec["worker_count"],
        "sdk_launcher": "adapters/cursor/sdk/run_workers.mjs",
        "workers": [
            {
                "task_id": w["task_id"],
                "session_name": w["session_name"],
                "cwd": w["cwd"],
                "prompt_path": w["prompt_path"],
                "prompt_source": w["prompt_source"],
                "headless_command": w["headless_command"],
                "result_report_paths": w["result_report_paths"],
            }
            for w in spec["workers"]
        ],
        "next_steps": [
            "Programmatic: cd adapters/cursor/sdk && npm install && CURSOR_SDK_RUN_SPEC=<run_spec> npm start",
            "Headless CLI: re-run with --print-commands and execute each line (cwd=workspace_root)",
            "After Workers finish: collect result reports, run gate sync + scope audit before delivery",
        ],
    }
    if spec["worker_count"] == 0:
        summary["note"] = "No write-permission Workers found in ownership.json"
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
