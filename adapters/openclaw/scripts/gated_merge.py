#!/usr/bin/env python3
"""Audit-enforced merge gate for multi-agent Worker branches (stdlib only).

Turns the scope audit from an advisory step a Main *should* run into a
code-enforced gate a Worker branch *must* pass before it can land.

Flow:
  1. Compute the files a Worker branch changed relative to the merge base.
  2. Run the (single source of truth) scope audit from ``audit_worker_output.py``
     against ONLY that Worker's ownership scope, in ``--strict`` mode.
  3. Merge the branch into the current base only when the audit passes.
     A failing audit refuses the merge and leaves the base tree untouched.

Default is dry-run (audit + verdict, no merge). Pass ``--execute`` to actually
land the branch on a clean audit. This mirrors the project convention
(``configure_mcp``/``run_graph`` default to dry-run, act only when told).

Return codes:
  0  audit passed (branch merged with --execute, or would-merge in dry-run)
  1  audit failed -> merge refused, base tree unchanged
  3  setup/git error (not a repo, missing branch, merge conflict, ...)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

AUDIT_SCRIPT = Path(__file__).resolve().parent / "audit_worker_output.py"


def run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def ensure_git_repo(repo_root: Path) -> tuple[bool, str]:
    if not repo_root.exists():
        return False, f"repo_root does not exist: {repo_root}"
    code, _, err = run_git(["rev-parse", "--is-inside-work-tree"], repo_root)
    if code != 0:
        return False, f"not a git work tree: {repo_root} ({err.strip()})"
    return True, "ok"


def current_branch(repo_root: Path) -> str:
    code, out, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    return out.strip() if code == 0 else "HEAD"


def branch_exists(repo_root: Path, ref: str) -> bool:
    code, _, _ = run_git(["rev-parse", "--verify", "--quiet", ref], repo_root)
    return code == 0


def changed_files_for_branch(repo_root: Path, base: str, branch: str) -> tuple[list[str], str]:
    """Return the paths a branch changed since it diverged from base (three-dot diff)."""
    code, out, err = run_git(
        ["diff", "--name-only", f"{base}...{branch}"], repo_root
    )
    if code != 0:
        return [], err.strip()
    files = [line.strip() for line in out.splitlines() if line.strip()]
    return files, ""


def load_ownership(ownership_path: Path) -> dict:
    return json.loads(ownership_path.read_text(encoding="utf-8-sig"))


def scoped_ownership(ownership: dict, task_id: str | None) -> tuple[dict, str | None]:
    """Restrict ownership to a single task so the gate is per-Worker precise.

    Without this, a file that lands in *another* task's allowed_paths would not
    be flagged as unowned — but a Worker touching a sibling Worker's scope is
    exactly the cross-scope leak the gate must catch.
    """
    if not task_id:
        return ownership, None
    tasks = ownership.get("tasks", [])
    match = [t for t in tasks if t.get("task_id") == task_id]
    if not match:
        known = ", ".join(t.get("task_id", "?") for t in tasks) or "(none)"
        return ownership, f"task_id {task_id!r} not found in ownership (have: {known})"
    scoped = dict(ownership)
    scoped["tasks"] = match
    return scoped, None


def run_audit(
    repo_root: Path,
    ownership: dict,
    changed: list[str],
    results_dir: Path | None,
    state_dir: str,
    write_audit: bool,
    strict: bool,
) -> tuple[dict, str]:
    """Invoke the canonical scope audit as a subprocess (single source of truth)."""
    with tempfile.TemporaryDirectory(prefix="gated-merge-") as tmp:
        tmp_path = Path(tmp)
        own_file = tmp_path / "ownership.json"
        own_file.write_text(json.dumps(ownership), encoding="utf-8")
        changed_file = tmp_path / "changed-files.txt"
        changed_file.write_text("\n".join(changed) + ("\n" if changed else ""), encoding="utf-8")

        cmd = [
            sys.executable,
            str(AUDIT_SCRIPT),
            "--ownership",
            str(own_file),
            "--changed-files",
            str(changed_file),
        ]
        if strict:
            cmd += ["--strict"]
        if results_dir:
            cmd += ["--results", str(results_dir)]
        if write_audit:
            cmd += ["--write-audit", "--state-dir", str((repo_root / state_dir))]
        proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
        try:
            report = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {}, f"audit produced no parseable report: {proc.stderr.strip() or proc.stdout.strip()}"
        return report, ""


def perform_merge(repo_root: Path, branch: str) -> tuple[bool, str]:
    code, out, err = run_git(["merge", "--no-ff", "--no-edit", branch], repo_root)
    if code == 0:
        return True, out.strip() or f"merged {branch}"
    # Undo a half-applied/conflicted merge so the base tree stays clean.
    run_git(["merge", "--abort"], repo_root)
    return False, f"git merge failed (aborted): {err.strip() or out.strip()}"


def gate(
    repo_root: Path,
    branch: str,
    ownership_path: Path,
    task_id: str | None = None,
    base: str | None = None,
    results_dir: Path | None = None,
    state_dir: str = ".codex-multi-agent",
    execute: bool = False,
    write_audit: bool = True,
) -> dict:
    ok, msg = ensure_git_repo(repo_root)
    if not ok:
        return {"ok": False, "gate": "error", "error": msg}

    if not branch_exists(repo_root, branch):
        return {"ok": False, "gate": "error", "error": f"branch not found: {branch}"}

    base = base or current_branch(repo_root)
    if not branch_exists(repo_root, base):
        return {"ok": False, "gate": "error", "error": f"base ref not found: {base}"}

    changed, err = changed_files_for_branch(repo_root, base, branch)
    if err:
        return {"ok": False, "gate": "error", "error": f"diff failed: {err}"}

    try:
        ownership = load_ownership(ownership_path)
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "gate": "error", "error": f"cannot read ownership: {exc}"}

    scoped, scope_err = scoped_ownership(ownership, task_id)
    if scope_err:
        return {"ok": False, "gate": "error", "error": scope_err}

    # Strict (report-aware) only when Worker result reports are supplied.
    strict = results_dir is not None
    report, audit_err = run_audit(
        repo_root, scoped, changed, results_dir, state_dir, write_audit, strict
    )
    if audit_err:
        return {"ok": False, "gate": "error", "error": audit_err}

    violations = report.get("violations", [])
    warnings = report.get("warnings", [])
    conflicts = report.get("conflicts", [])
    # Scope/secret signals always carry a concrete ``path`` (a secret path that
    # landed, or a changed file owned by no Worker). Report/completion concerns
    # (e.g. "result report not found") carry only a task_id. The merge gate
    # enforces the path-bearing class unconditionally; the report class matters
    # only when ``--results`` was supplied for false-completion checking.
    path_blocking = [e for e in (violations + warnings) if e.get("path")]
    if results_dir is not None:
        audit_pass = bool(report.get("ok"))
    else:
        audit_pass = not path_blocking and not conflicts

    result: dict = {
        "branch": branch,
        "base": base,
        "task_id": task_id,
        "changed_files": changed,
        "audit_ok": audit_pass,
        "blocking": (path_blocking + conflicts) if not audit_pass else [],
        "violations": violations,
        "conflicts": conflicts,
        "warnings": warnings,
    }

    if not audit_pass:
        result["ok"] = False
        result["gate"] = "refused"
        result["merged"] = False
        result["reason"] = "scope audit failed; merge refused, base tree unchanged"
        return result

    if not execute:
        result["ok"] = True
        result["gate"] = "would-merge"
        result["merged"] = False
        result["reason"] = "audit passed (dry-run); pass --execute to land the branch"
        return result

    merged, merge_msg = perform_merge(repo_root, branch)
    result["ok"] = merged
    result["gate"] = "merged" if merged else "error"
    result["merged"] = merged
    result["merge_detail"] = merge_msg
    if not merged:
        result["reason"] = merge_msg
    return result


# --------------------------------------------------------------------------- #
# Self-check: an adversarial test baked into the gate itself.
# --------------------------------------------------------------------------- #
def _git(args: list[str], cwd: Path) -> None:
    code, _, err = run_git(args, cwd)
    if code != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {err.strip()}")


def _seed_repo(root: Path) -> None:
    _git(["init", "-q", "-b", "main"], root)
    _git(["config", "user.email", "gate@local"], root)
    _git(["config", "user.name", "gate"], root)
    state = root / ".codex-multi-agent"
    state.mkdir(parents=True, exist_ok=True)
    ownership = {
        "schema_version": 1,
        "tasks": [
            {
                "task_id": "T001",
                "session_name": "worker-backend",
                "role": "Worker",
                "allowed_paths": ["src/**"],
                "blocked_paths": [".env"],
                "status": "pending",
            }
        ],
    }
    (state / "ownership.json").write_text(json.dumps(ownership), encoding="utf-8")
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(["add", "-A"], root)
    _git(["commit", "-q", "-m", "base"], root)


def _make_branch(root: Path, name: str, rel_path: str, content: str) -> None:
    _git(["checkout", "-q", "-b", name], root)
    target = root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(["add", "-A"], root)
    _git(["commit", "-q", "-m", f"work on {name}"], root)
    _git(["checkout", "-q", "main"], root)


def run_self_check() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="gated-merge-selfcheck-") as tmp:
        root = Path(tmp)
        _seed_repo(root)
        own = root / ".codex-multi-agent" / "ownership.json"

        # Clean in-scope branch -> must pass and merge.
        _make_branch(root, "multi-agent/T001-clean", "src/feature.py", "y = 2\n")
        clean = gate(root, "multi-agent/T001-clean", own, task_id="T001",
                     base="main", execute=True, write_audit=False)
        if not clean.get("merged"):
            errors.append(f"clean branch should merge, got: {clean.get('gate')} {clean.get('reason')}")
        if not (root / "src" / "feature.py").exists():
            errors.append("clean branch merged but file missing from base tree")

        # Secret-touching branch -> must be refused, base tree untouched.
        _make_branch(root, "multi-agent/T001-secret", "src/secrets/apikeys.json", "{}\n")
        secret = gate(root, "multi-agent/T001-secret", own, task_id="T001",
                      base="main", execute=True, write_audit=False)
        if secret.get("merged"):
            errors.append("secret branch was merged — gate FAILED to block a secret path")
        if (root / "src" / "secrets" / "apikeys.json").exists():
            errors.append("secret file leaked into base tree despite refusal")
        if secret.get("gate") != "refused":
            errors.append(f"secret branch expected gate=refused, got {secret.get('gate')}")

        # Out-of-scope branch (touches a sibling scope) -> refused in strict mode.
        _make_branch(root, "multi-agent/T001-oos", "other/x.py", "z = 3\n")
        oos = gate(root, "multi-agent/T001-oos", own, task_id="T001",
                   base="main", execute=True, write_audit=False)
        if oos.get("merged"):
            errors.append("out-of-scope branch was merged — gate FAILED to block scope leak")

        # Dry-run must never mutate the tree.
        _make_branch(root, "multi-agent/T001-dry", "src/dry.py", "d = 4\n")
        dry = gate(root, "multi-agent/T001-dry", own, task_id="T001",
                   base="main", execute=False)
        if dry.get("merged"):
            errors.append("dry-run must not merge")
        if (root / "src" / "dry.py").exists():
            errors.append("dry-run must not touch the base tree")

    if errors:
        print("gated_merge self-check FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("gated_merge self-check OK (clean merges, blocks secrets/out-of-scope, dry-run inert)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="Run built-in adversarial validation and exit")
    parser.add_argument("--repo-root", default=".", help="Repository root (default: cwd)")
    parser.add_argument("--branch", help="Worker branch to gate-merge (e.g. multi-agent/T002-worker-backend-<hash>)")
    parser.add_argument("--ownership", help="Path to ownership.json")
    parser.add_argument("--task-id", help="Gate against only this task's scope (recommended)")
    parser.add_argument("--base", help="Base ref to merge into (default: current branch)")
    parser.add_argument("--results", help="Optional Worker result-report dir for stricter false-completion checks")
    parser.add_argument("--state-dir", default=".codex-multi-agent", help="Mission-control dir for audit records")
    parser.add_argument("--execute", action="store_true", help="Actually merge on a clean audit (default: dry-run)")
    parser.add_argument("--no-write-audit", action="store_true", help="Do not persist an audit record")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    if not args.branch or not args.ownership:
        parser.error("--branch and --ownership are required unless --self-check is used")

    report = gate(
        repo_root=Path(args.repo_root).expanduser().resolve(),
        branch=args.branch,
        ownership_path=Path(args.ownership),
        task_id=args.task_id,
        base=args.base,
        results_dir=Path(args.results) if args.results else None,
        state_dir=args.state_dir,
        execute=args.execute,
        write_audit=not args.no_write_audit,
    )
    print(json.dumps(report, indent=2))
    if report.get("gate") == "error":
        return 3
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
