#!/usr/bin/env python3
"""Loop-engineering driver for the OpenClaw multi-agent framework (dependency-free).

Loop engineering = drive an agent inside a *controlled* loop until a verifiable
goal is met or a hard budget is hit (never an unbounded loop). Five elements:

  1. Goal     - an explicit, verifiable stop condition.
  2. Actions  - a ``maker`` performs one production step per iteration.
  3. Verify   - an *independent* ``verifier`` judges the maker output. The
                producer may not grade itself, so ``maker`` MUST be a different
                callable than ``verifier`` (maker != checker).
  4. Repair   - each verifier feedback is fed into the next maker call as
                ``last_feedback`` (diagnose-then-adjust, not blind retry).
  5. Memory   - every round is appended to a caller-supplied ``memory`` list so
                lessons persist across iterations.

Stop condition = verifier passes, OR ``max_iterations`` / ``budget`` is reached
(the loop is always bounded). The driver is generic and injectable:

    result = run_loop(goal, maker, verifier, max_iterations=5, memory=[])

A CLI wires a "real" loop where the maker dispatches Workers through
``scripts/run_multi_agent.py`` and the verifier runs a deterministic
``--verify-command`` (optionally AND-ed with ``audit_worker_output.py`` ok).
Real mode only runs when the user explicitly passes flags; ``--self-check`` is
fully deterministic and never touches the repo or any external CLI.

Examples:
  python adapters/openclaw/scripts/run_loop.py --self-check
  python adapters/openclaw/scripts/run_loop.py \\
      --task-card .codex-multi-agent/tasks/T002-worker-backend.md \\
      --runtime openclaw --verify-command "pytest -q" \\
      --max-iterations 4 --state-dir .codex-multi-agent --with-audit
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ADAPTER_ROOT = SCRIPT_DIR.parent
REPO_ROOT = ADAPTER_ROOT.parent.parent

VALID_STATUSES = {"passed", "exhausted", "rejected"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _coerce_maker_output(output: object) -> dict:
    """Maker is expected to return a dict; wrap anything else defensively."""
    if isinstance(output, dict):
        return output
    return {"output": output}


def _normalize_verdict(verdict: object) -> tuple[bool, str]:
    """Accept (passed, feedback) tuples, {'passed','feedback'} dicts, or a bare bool."""
    if isinstance(verdict, (tuple, list)):
        passed = bool(verdict[0]) if verdict else False
        feedback = verdict[1] if len(verdict) > 1 else ""
    elif isinstance(verdict, dict):
        passed = bool(verdict.get("passed"))
        feedback = verdict.get("feedback", "")
    else:
        passed = bool(verdict)
        feedback = ""
    if feedback is None:
        feedback = ""
    return passed, str(feedback)


def _rejected(goal: object, reason: str, **extra: object) -> dict:
    """Pre-flight guard result: bounded, never ran a maker/verifier round."""
    payload = {
        "ok": False,
        "status": "rejected",
        "iterations_run": 0,
        "history": [],
        "goal": goal,
        "stop_reason": reason,
    }
    payload.update(extra)
    return payload


def run_loop(
    goal: object,
    maker,
    verifier,
    *,
    max_iterations: int,
    memory: list | None = None,
    budget: dict | None = None,
) -> dict:
    """Drive ``maker`` -> ``verifier`` in a bounded repair loop until the goal is met.

    Args:
        goal: An explicit, verifiable stop condition (echoed into the result).
        maker(iteration, last_feedback) -> dict: performs one action and returns
            a result summary. ``last_feedback`` is ``None`` on the first round and
            the previous round's verifier feedback afterwards (the repair signal).
        verifier(maker_output) -> (passed: bool, feedback: str): independently
            judges whether the goal is met and returns actionable feedback. Also
            accepts a bare bool or a {"passed","feedback"} dict.
        max_iterations: Hard upper bound on rounds (loops are never unbounded).
        memory: Optional caller-owned list; one record is appended per round so
            lessons persist across iterations.
        budget: Optional dict with any of ``max_seconds`` (wall clock),
            ``max_cost`` (cumulative ``maker_output['cost']``), and
            ``max_iterations`` (may only tighten the cap).

    Returns:
        dict with keys: ``ok``, ``status`` ('passed' | 'exhausted' | 'rejected'),
        ``iterations_run``, ``history`` (list of {iteration, verifier_passed,
        feedback}), ``goal``, ``stop_reason``, and ``budget_spent``. A
        maker==verifier violation returns status 'rejected' with
        ``maker_is_checker_violation=True``.
    """
    # --- guard: maker != checker (the producer cannot grade itself) ---
    if maker is verifier:
        return _rejected(
            goal,
            "maker_is_checker_violation: maker and verifier must be distinct callables "
            "(the producer cannot grade itself)",
            maker_is_checker_violation=True,
        )
    if not callable(maker) or not callable(verifier):
        return _rejected(goal, "maker and verifier must both be callable")

    try:
        max_iterations = int(max_iterations)
    except (TypeError, ValueError):
        return _rejected(goal, "max_iterations must be an integer >= 1")
    if max_iterations < 1:
        return _rejected(goal, "max_iterations must be >= 1 (loops are always bounded)")

    if memory is not None and not hasattr(memory, "append"):
        return _rejected(goal, "memory must be a list (or support .append)")

    budget = budget or {}
    max_seconds = budget.get("max_seconds")
    max_cost = budget.get("max_cost")
    budget_iterations = budget.get("max_iterations")
    if isinstance(budget_iterations, int) and budget_iterations >= 1:
        # budget may only tighten the cap, never loosen it
        max_iterations = min(max_iterations, budget_iterations)

    history: list[dict] = []
    last_feedback: str | None = None
    cost_spent = 0.0
    started = time.monotonic()
    status = "exhausted"
    stop_reason = f"reached max_iterations={max_iterations} without passing verifier"
    iterations_run = 0

    for iteration in range(1, max_iterations + 1):
        # --- budget gate (checked before more work; keeps the loop bounded) ---
        elapsed = time.monotonic() - started
        if max_seconds is not None and elapsed >= max_seconds:
            status = "exhausted"
            stop_reason = f"budget_exhausted: max_seconds={max_seconds} (elapsed={elapsed:.4f})"
            break
        if max_cost is not None and cost_spent >= max_cost:
            status = "exhausted"
            stop_reason = f"budget_exhausted: max_cost={max_cost} (spent={cost_spent})"
            break

        # --- action: the maker changes the environment ---
        round_error: str | None = None
        try:
            maker_output = _coerce_maker_output(maker(iteration, last_feedback))
            maker_ok = bool(maker_output.get("ok", True))
        except Exception as exc:  # repair philosophy: capture and feed it forward
            maker_output = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            maker_ok = False
            round_error = maker_output["error"]

        cost_spent += float(maker_output.get("cost", 0) or 0)
        iterations_run = iteration

        # --- verify: independent judge (maker != checker enforced above) ---
        if round_error is not None:
            passed = False
            feedback = f"maker raised before verification: {round_error}"
        else:
            try:
                passed, feedback = _normalize_verdict(verifier(maker_output))
            except Exception as exc:
                passed = False
                feedback = f"verifier raised: {type(exc).__name__}: {exc}"
                round_error = feedback

        entry = {"iteration": iteration, "verifier_passed": passed, "feedback": feedback}
        if round_error is not None:
            entry["error"] = True
        history.append(entry)

        # --- memory: persist every round so lessons carry across iterations ---
        if memory is not None:
            memory.append(
                {
                    "iteration": iteration,
                    "ts": utc_now(),
                    "verifier_passed": passed,
                    "feedback": feedback,
                    "maker_ok": maker_ok,
                    "maker_output": maker_output,
                }
            )

        if passed:
            status = "passed"
            stop_reason = f"verifier passed on iteration {iteration}"
            break

        # --- repair: feed this round's feedback into the next maker call ---
        last_feedback = feedback

    return {
        "ok": status == "passed",
        "status": status,
        "iterations_run": iterations_run,
        "history": history,
        "goal": goal,
        "stop_reason": stop_reason,
        "budget_spent": {
            "iterations": iterations_run,
            "cost": cost_spent,
            "seconds": round(time.monotonic() - started, 6),
        },
    }


# --------------------------------------------------------------------------- #
# Real mode: maker = run_multi_agent.py, verifier = --verify-command (+audit)  #
# --------------------------------------------------------------------------- #


def _build_real_maker(
    repo_root: Path,
    runtime: str,
    task_card: Path,
    state_dir: str | None,
    *,
    mode: str | None = None,
    timeout: float | None = None,
):
    """Maker that dispatches one Worker round via scripts/run_multi_agent.py."""
    run_multi_agent = repo_root / "scripts" / "run_multi_agent.py"

    def maker(iteration: int, last_feedback: str | None) -> dict:
        if not run_multi_agent.is_file():
            return {"ok": False, "error": f"run_multi_agent.py not found: {run_multi_agent}"}
        cmd = [
            sys.executable,
            str(run_multi_agent),
            "--runtime",
            runtime,
            "--task-card",
            str(task_card),
        ]
        if state_dir:
            cmd += ["--state-dir", str(state_dir)]
        if mode:
            cmd += ["--mode", mode]
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
        return {
            "ok": proc.returncode == 0,
            "action": "run_multi_agent",
            "iteration": iteration,
            "received_feedback": last_feedback,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "").strip()[-2000:],
            "stderr_tail": (proc.stderr or "").strip()[-2000:],
        }

    return maker


def _run_audit_gate(repo_root: Path, state_dir: str | None) -> tuple[bool | None, str]:
    """Layer the scope audit gate on top of the verify command (independent check)."""
    audit_script = SCRIPT_DIR / "audit_worker_output.py"
    base = Path(state_dir) if state_dir else Path(".codex-multi-agent")
    ownership = base / "ownership.json"
    results = base / "results"
    changed = base / "changed-files.txt"
    if not audit_script.is_file() or not ownership.is_file():
        return None, "audit skipped (missing audit_worker_output.py or ownership.json)"
    cmd = [sys.executable, str(audit_script), "--ownership", str(ownership), "--results", str(results)]
    if changed.is_file():
        cmd += ["--changed-files", str(changed)]
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        report = json.loads(proc.stdout)
        gate = report.get("gate", {}) if isinstance(report, dict) else {}
        ok = bool(report.get("ok"))
        detail = (
            f"audit gate={gate.get('status')} ok={report.get('ok')} "
            f"violations={len(report.get('violations', []))} conflicts={len(report.get('conflicts', []))}"
        )
        return ok, detail
    except (json.JSONDecodeError, AttributeError):
        return proc.returncode == 0, f"audit rc={proc.returncode}"


def _build_real_verifier(
    verify_command: str,
    repo_root: Path,
    *,
    with_audit: bool = False,
    state_dir: str | None = None,
    timeout: float | None = None,
):
    """Independent verifier: shell command (rc 0 == passed), optionally AND audit ok."""

    def verifier(maker_output: dict) -> tuple[bool, str]:
        proc = subprocess.run(
            verify_command,
            shell=True,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
        passed = proc.returncode == 0
        parts = [f"verify_command rc={proc.returncode}"]
        out_tail = (proc.stdout or "").strip()[-1000:]
        err_tail = (proc.stderr or "").strip()[-1000:]
        if out_tail:
            parts.append(f"stdout: {out_tail}")
        if err_tail:
            parts.append(f"stderr: {err_tail}")
        if with_audit:
            audit_ok, audit_detail = _run_audit_gate(repo_root, state_dir)
            parts.append(audit_detail)
            if audit_ok is False:
                passed = False  # audit gate not passed -> goal not met
        return passed, " | ".join(parts)

    return verifier


def invoke(payload: dict) -> dict:
    """Run the real loop from a JSON-friendly payload (no-op for missing inputs)."""
    verify_command = payload.get("verify_command")
    task_card = payload.get("task_card")
    if not verify_command:
        return {"ok": False, "error": "verify_command is required for real mode (the independent verifier)"}
    if not task_card:
        return {"ok": False, "error": "task_card is required for real mode (maker dispatches it via run_multi_agent.py)"}

    repo_root = Path(payload.get("repo_root") or REPO_ROOT).expanduser().resolve()
    runtime = payload.get("runtime") or "openclaw"
    state_dir = payload.get("state_dir") or ".codex-multi-agent"
    mode = payload.get("mode")
    with_audit = bool(payload.get("with_audit"))
    try:
        max_iterations = int(payload.get("max_iterations", 5))
    except (TypeError, ValueError):
        return {"ok": False, "error": "max_iterations must be an integer"}
    timeout = payload.get("timeout")

    budget: dict = {}
    if payload.get("budget_seconds") is not None:
        budget["max_seconds"] = float(payload["budget_seconds"])
    if payload.get("budget_cost") is not None:
        budget["max_cost"] = float(payload["budget_cost"])

    task_card_path = Path(task_card).expanduser().resolve()
    if not task_card_path.is_file():
        return {"ok": False, "error": f"task card not found: {task_card_path}"}

    goal = payload.get("goal") or {
        "verify_command": verify_command,
        "task_card": str(task_card_path),
        "with_audit": with_audit,
        "stop_when": "verify_command returncode 0" + (" AND audit gate ok" if with_audit else ""),
    }

    maker = _build_real_maker(repo_root, runtime, task_card_path, state_dir, mode=mode, timeout=timeout)
    verifier = _build_real_verifier(
        verify_command, repo_root, with_audit=with_audit, state_dir=state_dir, timeout=timeout
    )
    memory: list[dict] = []
    result = run_loop(
        goal,
        maker,
        verifier,
        max_iterations=max_iterations,
        memory=memory,
        budget=budget or None,
    )
    result["memory"] = memory
    return result


# --------------------------------------------------------------------------- #
# Self-check: fully deterministic, no external CLI, no repo writes             #
# --------------------------------------------------------------------------- #


def run_self_check() -> int:
    errors: list[str] = []
    goal = "fake goal: verifier returns passed"

    def maker_seq(iteration, last_feedback):
        return {"iteration": iteration, "ok": True}

    def verifier_at_k(k):
        def _verify(maker_output):
            it = maker_output.get("iteration", 0)
            if it >= k:
                return True, f"passed at iteration {it}"
            return False, f"not yet: at {it}, need {k}"

        return _verify

    def verifier_never(maker_output):
        return False, "never converges"

    # 1) Convergence: maker makes verifier pass on iteration k.
    conv = run_loop(goal, maker_seq, verifier_at_k(3), max_iterations=10, memory=[])
    if conv.get("status") != "passed":
        errors.append(f"convergence: expected status=passed, got {conv.get('status')}")
    if conv.get("iterations_run") != 3:
        errors.append(f"convergence: expected iterations_run==3, got {conv.get('iterations_run')}")
    if not conv.get("ok"):
        errors.append("convergence: ok should be True when passed")
    if len(conv.get("history", [])) != 3 or not conv["history"][-1]["verifier_passed"]:
        errors.append("convergence: history should hold 3 entries ending in a pass")

    # 2) Non-convergence stays bounded (proves no infinite loop).
    exhaust = run_loop(goal, maker_seq, verifier_never, max_iterations=5, memory=[])
    if exhaust.get("status") != "exhausted":
        errors.append(f"exhaustion: expected status=exhausted, got {exhaust.get('status')}")
    if exhaust.get("iterations_run") != 5:
        errors.append(f"exhaustion: expected iterations_run==max_iterations==5, got {exhaust.get('iterations_run')}")
    if exhaust.get("ok"):
        errors.append("exhaustion: ok must be False when never passed")

    # 3) Repair: maker round n receives verifier feedback from round n-1.
    received: list = []

    def maker_record(iteration, last_feedback):
        received.append(last_feedback)
        return {"iteration": iteration}

    def verifier_feedback(maker_output):
        it = maker_output.get("iteration", 0)
        return it >= 3, f"fix-{it}"

    repair = run_loop(goal, maker_record, verifier_feedback, max_iterations=5, memory=[])
    if received[:3] != [None, "fix-1", "fix-2"]:
        errors.append(f"repair: feedback not threaded into next maker call, received={received}")
    if repair.get("iterations_run") != 3:
        errors.append(f"repair: expected pass on iteration 3, got {repair.get('iterations_run')}")

    # 4) maker != checker: same callable for both is detected and rejected.
    def same_callable(*args, **kwargs):
        return {"iteration": 1}

    violation = run_loop(goal, same_callable, same_callable, max_iterations=3, memory=[])
    if not violation.get("maker_is_checker_violation"):
        errors.append("maker!=checker: one callable as both must set maker_is_checker_violation")
    if violation.get("ok") or violation.get("status") != "rejected":
        errors.append(f"maker!=checker: must be rejected, got status={violation.get('status')}")
    if violation.get("iterations_run") != 0:
        errors.append("maker!=checker: violation must not run any iteration")

    # 5) Memory records every round.
    mem: list = []
    mem_run = run_loop(goal, maker_seq, verifier_at_k(4), max_iterations=10, memory=mem)
    if len(mem) != mem_run.get("iterations_run"):
        errors.append(f"memory: expected {mem_run.get('iterations_run')} entries, got {len(mem)}")
    if not all("iteration" in e and "feedback" in e for e in mem):
        errors.append("memory: each entry must carry iteration and feedback")
    if [e["iteration"] for e in mem] != [1, 2, 3, 4]:
        errors.append(f"memory: rounds not logged in order, got {[e.get('iteration') for e in mem]}")

    # 6) Budget caps the loop independently of max_iterations.
    def maker_cost(iteration, last_feedback):
        return {"iteration": iteration, "cost": 1}

    budgeted = run_loop(
        goal, maker_cost, verifier_never, max_iterations=100, memory=[], budget={"max_cost": 3}
    )
    if budgeted.get("iterations_run") != 3:
        errors.append(f"budget: max_cost=3 should stop after 3 unit-cost rounds, got {budgeted.get('iterations_run')}")
    if "budget_exhausted" not in budgeted.get("stop_reason", ""):
        errors.append(f"budget: stop_reason should cite the budget, got {budgeted.get('stop_reason')!r}")

    seconds = run_loop(
        goal, maker_seq, verifier_never, max_iterations=10, memory=[], budget={"max_seconds": 0}
    )
    if seconds.get("status") != "exhausted" or "max_seconds" not in seconds.get("stop_reason", ""):
        errors.append(f"budget: max_seconds=0 should stop immediately, got {seconds.get('stop_reason')!r}")

    # 7) Guard rails: invalid max_iterations and bad memory are rejected (still bounded).
    if run_loop(goal, maker_seq, verifier_never, max_iterations=0, memory=[]).get("status") != "rejected":
        errors.append("guard: max_iterations<1 must be rejected")
    if run_loop(goal, maker_seq, verifier_never, max_iterations=3, memory=42).get("status") != "rejected":
        errors.append("guard: non-list memory must be rejected")

    # 8) Verdict normalization accepts tuple / bool / dict shapes.
    if _normalize_verdict((True, "ok")) != (True, "ok"):
        errors.append("verdict: tuple form not normalized")
    if _normalize_verdict(True) != (True, ""):
        errors.append("verdict: bool form not normalized")
    if _normalize_verdict({"passed": True, "feedback": "y"}) != (True, "y"):
        errors.append("verdict: dict form not normalized")

    # 9) Maker exceptions are captured as repair feedback and stay bounded.
    def maker_boom(iteration, last_feedback):
        raise RuntimeError("boom")

    boom = run_loop(goal, maker_boom, verifier_never, max_iterations=2, memory=[])
    if boom.get("status") != "exhausted" or boom.get("iterations_run") != 2:
        errors.append("exceptions: maker errors must be captured and the loop stay bounded")
    if not all(e.get("error") for e in boom.get("history", [])):
        errors.append("exceptions: maker error rounds should be flagged in history")

    # 10) CLI/real-mode plumbing rejects missing inputs WITHOUT running anything.
    miss_cmd = invoke({})
    if miss_cmd.get("ok") or "verify_command" not in miss_cmd.get("error", ""):
        errors.append("invoke: missing verify_command must be rejected")
    miss_card = invoke({"verify_command": "true"})
    if miss_card.get("ok") or "task_card" not in miss_card.get("error", ""):
        errors.append("invoke: missing task_card must be rejected")
    miss_file = invoke({"verify_command": "true", "task_card": str(SCRIPT_DIR / "does-not-exist-xyz.md")})
    if miss_file.get("ok") or "task card not found" not in miss_file.get("error", ""):
        errors.append("invoke: nonexistent task card must be rejected before running anything")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "run_loop self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--self-check", action="store_true", help="Run built-in deterministic validation and exit")
    parser.add_argument("--task-card", help="Path to .codex-multi-agent/tasks/*.md (maker dispatches via run_multi_agent.py)")
    parser.add_argument("--verify-command", help="Shell command; returncode 0 => verifier passed (independent of maker)")
    parser.add_argument("--runtime", default="openclaw", help="Runtime passed to run_multi_agent.py")
    parser.add_argument("--mode", help="Optional mode passed to run_multi_agent.py (claude-code: local|acp)")
    parser.add_argument("--max-iterations", type=int, default=5, help="Hard upper bound on loop iterations")
    parser.add_argument("--state-dir", default=".codex-multi-agent", help="Mission-control state dir (for the audit gate)")
    parser.add_argument("--with-audit", action="store_true", help="AND the verifier with audit_worker_output.py ok")
    parser.add_argument("--repo-root", help="Repo root containing scripts/run_multi_agent.py (default: inferred)")
    parser.add_argument("--budget-seconds", type=float, help="Optional wall-clock budget cap")
    parser.add_argument("--budget-cost", type=float, help="Optional cumulative cost budget (maker may report 'cost')")
    parser.add_argument("--timeout", type=float, help="Per-subprocess timeout in seconds (real mode)")
    parser.add_argument("--json-in", help="JSON input string with the same keys (otherwise flags or stdin)")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    flags_provided = any(
        [
            args.task_card,
            args.verify_command,
            args.with_audit,
            args.repo_root,
            args.mode,
            args.budget_seconds is not None,
            args.budget_cost is not None,
            args.timeout is not None,
        ]
    )

    # Prefer explicit flags. Only read JSON from stdin when no flags were given
    # and stdin is actually piped, so flag-based use from a non-TTY subprocess
    # never blocks waiting on stdin.
    if args.json_in is not None:
        try:
            payload = json.loads(args.json_in)
        except json.JSONDecodeError as exc:
            print(json.dumps({"ok": False, "error": f"invalid --json-in: {exc}"}, indent=2))
            return 1
    elif not flags_provided and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
        if not text:
            parser.error("no input: pass --task-card and --verify-command, --json-in, or JSON on stdin")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            print(json.dumps({"ok": False, "error": f"invalid stdin JSON: {exc}"}, indent=2))
            return 1
    elif not args.task_card and not args.verify_command:
        parser.error(
            "real mode requires --task-card and --verify-command (or use --self-check). "
            "Default does not run external commands."
        )
        return 2  # unreachable; parser.error exits
    else:
        payload = {
            "task_card": args.task_card,
            "verify_command": args.verify_command,
            "runtime": args.runtime,
            "mode": args.mode,
            "max_iterations": args.max_iterations,
            "state_dir": args.state_dir,
            "with_audit": args.with_audit,
            "repo_root": args.repo_root,
            "budget_seconds": args.budget_seconds,
            "budget_cost": args.budget_cost,
            "timeout": args.timeout,
        }

    if not isinstance(payload, dict):
        print(json.dumps({"ok": False, "error": "JSON input must be an object"}, indent=2))
        return 1

    result = invoke(payload)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
