#!/usr/bin/env python3
"""Dependency-ordered scheduler for the multi-agent task graph (dependency-free).

Operationalizes the auto-unblock signal: instead of Main hand-picking the next
task, this driver repeatedly (1) syncs status, (2) asks which tasks are
``ready_to_spawn`` (dependencies satisfied), (3) dispatches each ready task, and
(4) re-evaluates — until every task is ``completed``, the graph deadlocks (no
ready tasks but work remains, e.g. a blocked/failed prerequisite), or a bounded
``max_rounds`` cap is hit. The loop is always bounded.

The scheduler is injectable and pure-ish: ``schedule_graph`` takes a ``dispatch``
callable so it can be unit-tested with a fake dispatcher (``--self-check`` does
exactly this, with no external CLI and no repo writes). Real mode dispatches each
ready task via ``scripts/run_multi_agent.py`` and only runs when the user passes
explicit flags.

Examples:
  python adapters/openclaw/scripts/run_graph.py --self-check
  python adapters/openclaw/scripts/run_graph.py \\
      --state-dir .codex-multi-agent --runtime openclaw --max-rounds 8 --execute
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent

from update_task_status import read_json, readiness_report, sync_status  # noqa: E402

TERMINAL_BLOCKERS = {"blocked", "failed"}


def _task_status_map(status_doc: dict) -> dict[str, str]:
    return {
        task_id: entry.get("status", "pending")
        for task_id, entry in (status_doc.get("tasks") or {}).items()
    }


def all_completed(status_map: dict[str, str]) -> bool:
    return bool(status_map) and all(s == "completed" for s in status_map.values())


def find_task_card(state_dir: Path, task_id: str) -> Path | None:
    tasks_dir = state_dir / "tasks"
    if not tasks_dir.is_dir():
        return None
    matches = sorted(tasks_dir.glob(f"{task_id}-*.md"))
    return matches[0] if matches else None


def schedule_graph(
    state_dir: Path,
    dispatch,
    *,
    max_rounds: int = 20,
) -> dict:
    """Drive the task graph in dependency order using ``dispatch(task_id, entry)``.

    ``dispatch`` performs one task (in real mode: launch a Worker/agent) and is
    expected to cause that task's result report to land so the next sync marks it
    ``completed``. Returns a structured, bounded result.
    """
    if not callable(dispatch):
        return {"ok": False, "status": "rejected", "error": "dispatch must be callable", "rounds": 0}
    try:
        max_rounds = int(max_rounds)
    except (TypeError, ValueError):
        return {"ok": False, "status": "rejected", "error": "max_rounds must be an integer", "rounds": 0}
    if max_rounds < 1:
        return {"ok": False, "status": "rejected", "error": "max_rounds must be >= 1 (always bounded)", "rounds": 0}

    history: list[dict] = []
    dispatched_order: list[str] = []
    rounds = 0
    status = "exhausted"
    stop_reason = f"reached max_rounds={max_rounds} before all tasks completed"

    while rounds < max_rounds:
        rounds += 1
        status_doc = sync_status(state_dir)
        status_map = _task_status_map(status_doc)
        readiness = readiness_report(status_doc)
        ready = readiness["ready"]

        if all_completed(status_map):
            status = "done"
            stop_reason = "all tasks completed"
            history.append({"round": rounds, "ready": [], "dispatched": [], "note": "all completed"})
            break

        if not ready:
            # No ready work but not all done -> deadlock (blocked/failed prereq or cycle).
            blockers = {
                tid: s for tid, s in status_map.items() if s in TERMINAL_BLOCKERS
            }
            status = "deadlock"
            stop_reason = (
                f"no ready tasks but {sum(1 for s in status_map.values() if s != 'completed')} "
                f"task(s) incomplete; terminal blockers={blockers or 'none'}, blocked_by={readiness['blocked']}"
            )
            history.append({"round": rounds, "ready": [], "dispatched": [], "blocked": readiness["blocked"], "blockers": blockers})
            break

        round_dispatched: list[str] = []
        for task_id in ready:
            entry = (status_doc.get("tasks") or {}).get(task_id, {})
            outcome = dispatch(task_id, entry)
            round_dispatched.append(task_id)
            dispatched_order.append(task_id)
            history.append({"round": rounds, "task_id": task_id, "dispatch": outcome})

        # Safety: if a full round dispatched nothing actionable, stop to stay bounded.
        if not round_dispatched:
            status = "deadlock"
            stop_reason = "round produced no dispatch"
            break

    final_doc = sync_status(state_dir)
    final_map = _task_status_map(final_doc)
    if all_completed(final_map) and status != "done":
        status = "done"
        stop_reason = "all tasks completed after final sync"

    return {
        "ok": status == "done",
        "status": status,
        "rounds": rounds,
        "dispatched": dispatched_order,
        "stop_reason": stop_reason,
        "final_statuses": final_map,
        "history": history,
    }


def _real_dispatch(state_dir: Path, runtime: str, repo_root: Path, timeout: float | None):
    run_multi_agent = repo_root / "scripts" / "run_multi_agent.py"

    def dispatch(task_id: str, entry: dict) -> dict:
        card = find_task_card(state_dir, task_id)
        if card is None:
            return {"ok": False, "error": f"no task card found for {task_id}"}
        if not run_multi_agent.is_file():
            return {"ok": False, "error": f"run_multi_agent.py not found: {run_multi_agent}"}
        cmd = [
            sys.executable,
            str(run_multi_agent),
            "--runtime",
            runtime,
            "--task-card",
            str(card),
            "--state-dir",
            str(state_dir),
        ]
        proc = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False, timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "task_id": task_id,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "").strip()[-1000:],
            "stderr_tail": (proc.stderr or "").strip()[-1000:],
        }

    return dispatch


def run_self_check() -> int:
    import tempfile

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="run-graph-selfcheck-") as tmp:
        state_dir = Path(tmp) / ".codex-multi-agent"
        results_dir = state_dir / "results"
        results_dir.mkdir(parents=True)

        def rp(task_id: str, session: str) -> dict[str, str]:
            return {
                "json": str(results_dir / f"{task_id}-{session}.json"),
                "md": str(results_dir / f"{task_id}-{session}.md"),
            }

        # Chain: T001 (Explorer) -> T002 (Worker dep T001) -> T003 (Reviewer dep T002).
        specs = [
            ("T001", "explorer-x", "Explorer", []),
            ("T002", "worker-x", "Worker", ["T001"]),
            ("T003", "reviewer-x", "Reviewer", ["T002"]),
        ]
        ownership = {
            "schema_version": 1,
            "task": "graph schedule self-check",
            "workspace_root": str(state_dir),
            "tasks": [
                {
                    "task_id": tid,
                    "session_name": sess,
                    "role": role,
                    "write_permission": role == "Worker",
                    "allowed_paths": ["**/*"],
                    "required_paths": [],
                    "dependencies": deps,
                    "result_report_json": rp(tid, sess)["json"],
                    "result_report_markdown": rp(tid, sess)["md"],
                    "status": "pending",
                }
                for tid, sess, role, deps in specs
            ],
        }
        from update_task_status import write_json  # local import to reuse writer

        write_json(state_dir / "ownership.json", ownership)

        # Fake dispatcher: completes a task by writing a clean result report.
        completed_calls: list[str] = []

        def fake_dispatch(task_id: str, entry: dict) -> dict:
            completed_calls.append(task_id)
            spec = next(s for s in specs if s[0] == task_id)
            sess, role = spec[1], spec[2]
            Path(rp(task_id, sess)["json"]).write_text(
                json.dumps({"task_id": task_id, "role": role, "status": "completed", "files_changed": []}),
                encoding="utf-8",
            )
            return {"ok": True, "task_id": task_id}

        result = schedule_graph(state_dir, fake_dispatch, max_rounds=10)
        if result["status"] != "done" or not result["ok"]:
            errors.append(f"schedule should complete the chain, got {result['status']} ({result['stop_reason']})")
        # Must dispatch in dependency order.
        if completed_calls != ["T001", "T002", "T003"]:
            errors.append(f"dispatch order should respect dependencies, got {completed_calls}")
        if result["final_statuses"].get("T003") != "completed":
            errors.append("final status should mark all tasks completed")

        # Deadlock: a Worker whose prerequisite never completes.
        dl_state = Path(tmp) / "deadlock"
        dl_results = dl_state / "results"
        dl_results.mkdir(parents=True)
        dl_ownership = {
            "schema_version": 1,
            "task": "deadlock",
            "workspace_root": str(dl_state),
            "tasks": [
                {
                    "task_id": "T001", "session_name": "explorer-x", "role": "Explorer",
                    "write_permission": False, "allowed_paths": ["**/*"], "required_paths": [],
                    "dependencies": [], "result_report_json": str(dl_results / "T001-explorer-x.json"),
                    "result_report_markdown": str(dl_results / "T001-explorer-x.md"), "status": "pending",
                },
                {
                    "task_id": "T002", "session_name": "worker-x", "role": "Worker",
                    "write_permission": True, "allowed_paths": ["**/*"], "required_paths": [],
                    "dependencies": ["T001"], "result_report_json": str(dl_results / "T002-worker-x.json"),
                    "result_report_markdown": str(dl_results / "T002-worker-x.md"), "status": "pending",
                },
            ],
        }
        write_json(dl_state / "ownership.json", dl_ownership)

        # Dispatcher that never completes anything -> ready set never shrinks past T001,
        # T001 stays pending, so it keeps dispatching T001 each round -> exhausts bound.
        def noop_dispatch(task_id: str, entry: dict) -> dict:
            return {"ok": False, "task_id": task_id, "note": "no result written"}

        dl_result = schedule_graph(dl_state, noop_dispatch, max_rounds=3)
        if dl_result["status"] not in {"exhausted", "deadlock"}:
            errors.append(f"non-completing dispatch must stay bounded, got {dl_result['status']}")
        if dl_result["ok"]:
            errors.append("non-completing schedule must not report ok")
        if dl_result["rounds"] > 3:
            errors.append("scheduler must respect max_rounds bound")

        # Guard rails.
        if schedule_graph(dl_state, fake_dispatch, max_rounds=0)["status"] != "rejected":
            errors.append("max_rounds<1 must be rejected")
        if schedule_graph(dl_state, None, max_rounds=5)["status"] != "rejected":
            errors.append("non-callable dispatch must be rejected")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "run_graph self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--self-check", action="store_true", help="Run deterministic validation and exit")
    parser.add_argument("--state-dir", default=".codex-multi-agent", help="Mission-control state directory")
    parser.add_argument("--runtime", default="openclaw", help="Runtime passed to run_multi_agent.py for each ready task")
    parser.add_argument("--max-rounds", type=int, default=20, help="Hard upper bound on scheduling rounds")
    parser.add_argument("--repo-root", help="Repo root containing scripts/run_multi_agent.py (default: inferred)")
    parser.add_argument("--timeout", type=float, help="Per-dispatch subprocess timeout in seconds")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually dispatch ready tasks via run_multi_agent.py (default: refuse, to avoid surprise launches)",
    )
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    state_dir = Path(args.state_dir).expanduser().resolve()
    if not (state_dir / "ownership.json").is_file():
        print(json.dumps({"ok": False, "error": f"ownership.json not found in {state_dir}"}, indent=2))
        return 1

    if not args.execute:
        # Safe default: show the dependency-ordered plan without launching anything.
        status_doc = sync_status(state_dir)
        readiness = readiness_report(status_doc)
        print(
            json.dumps(
                {
                    "ok": True,
                    "mode": "plan",
                    "note": "Dry plan only. Re-run with --execute to dispatch ready tasks via run_multi_agent.py.",
                    "current_phase": status_doc.get("current_phase"),
                    **readiness,
                },
                indent=2,
            )
        )
        return 0

    repo_root = Path(args.repo_root).expanduser().resolve() if args.repo_root else REPO_ROOT
    dispatch = _real_dispatch(state_dir, args.runtime, repo_root, args.timeout)
    result = schedule_graph(state_dir, dispatch, max_rounds=args.max_rounds)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
