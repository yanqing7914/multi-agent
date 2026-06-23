#!/usr/bin/env python3
"""Dependency-free git worktree helper for parallel multi-agent Workers.

Industry practice (Cursor Agents, Claude Code worktrees, Superset) isolates each
parallel coding agent in its own git worktree + branch so that simultaneous
Workers cannot overwrite each other's files. This project already divides work
*logically* via `ownership.allowed_paths` and catches collisions *after the fact*
via `audit_worker_output.py`; this tool adds the missing *physical* isolation
layer and maps it straight onto `ownership.json` (one worktree per Worker).

Actions:
  create  Create one isolated worktree+branch for a task.
  list    List the repo's worktrees (parsed `git worktree list --porcelain`).
  remove  Remove a worktree (optionally delete its branch).
  plan    From an ownership.json, plan/create one worktree per Worker.

Examples:
  python tools/worktree_tool.py --action create --repo-root . --task-id T002 --session-name worker-backend
  python tools/worktree_tool.py --action plan --ownership .codex-multi-agent/ownership.json --create
  python tools/worktree_tool.py --action remove --repo-root . --path ../repo.worktrees/multi-agent-T002-worker-backend --delete-branch
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from _tool_base import (
    emit_json,
    load_json_input,
    normalize_path,
    resolve_repo_root,
    tool_result,
)

BRANCH_PREFIX = "multi-agent"


def run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def ensure_git_repo(repo_root: Path) -> tuple[bool, str]:
    if not shutil.which("git"):
        return False, "git binary not found on PATH"
    if not repo_root.exists():
        return False, f"repo_root does not exist: {repo_root}"
    code, _, err = run_git(["rev-parse", "--is-inside-work-tree"], repo_root)
    if code != 0:
        return False, f"not a git work tree: {repo_root} ({err.strip()})"
    return True, "ok"


def sanitize_segment(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "-" for ch in (value or "").strip())
    return safe.strip("-") or "task"


def branch_for(task_id: str, session_name: str | None = None) -> str:
    parts = [sanitize_segment(task_id)]
    if session_name:
        parts.append(sanitize_segment(session_name))
    return f"{BRANCH_PREFIX}/" + "-".join(parts)


def worktrees_root_for(repo_root: Path, override: str | Path | None = None) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    # Default to a sibling directory so worktrees never pollute the main tree's
    # `git status` (which would corrupt scope audits).
    return repo_root.parent / f"{repo_root.name}.worktrees"


def branch_exists(repo_root: Path, branch: str) -> bool:
    code, _, _ = run_git(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"], repo_root)
    return code == 0


def worktree_create(
    repo_root: Path,
    task_id: str,
    session_name: str | None = None,
    branch: str | None = None,
    base_ref: str | None = None,
    worktrees_root: str | Path | None = None,
    setup: str | None = None,
    force: bool = False,
) -> dict:
    ok, msg = ensure_git_repo(repo_root)
    if not ok:
        return tool_result(False, action="create", error=msg)

    branch = branch or branch_for(task_id, session_name)
    wt_root = worktrees_root_for(repo_root, worktrees_root)
    path = wt_root / branch.replace("/", "-")

    if path.exists() and not force:
        return tool_result(
            False,
            action="create",
            error=f"worktree path already exists (use force to reuse): {path}",
            worktree_path=str(path),
            branch=branch,
        )

    wt_root.mkdir(parents=True, exist_ok=True)
    existed = branch_exists(repo_root, branch)

    add_args = ["worktree", "add"]
    if force:
        add_args.append("--force")
    if existed:
        add_args += [str(path), branch]
    else:
        add_args += ["-b", branch, str(path)]
        if base_ref:
            add_args.append(base_ref)

    code, out, err = run_git(add_args, repo_root)
    if code != 0:
        return tool_result(
            False,
            action="create",
            error=(err or out).strip(),
            returncode=code,
            attempted=" ".join(add_args),
        )

    setup_result = None
    if setup:
        proc = subprocess.run(
            setup,
            cwd=str(path),
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        setup_result = {
            "command": setup,
            "returncode": proc.returncode,
            "ok": proc.returncode == 0,
            "stderr_tail": (proc.stderr or "").strip()[-500:],
        }

    return tool_result(
        True,
        action="create",
        worktree_path=str(path),
        branch=branch,
        base_ref=base_ref or "HEAD",
        task_id=task_id,
        session_name=session_name,
        branch_existed=existed,
        setup=setup_result,
        hint="Point this Worker's workspace_root at worktree_path; collect its result report, then merge/PR the branch.",
    )


def worktree_list(repo_root: Path) -> dict:
    ok, msg = ensure_git_repo(repo_root)
    if not ok:
        return tool_result(False, action="list", error=msg)
    code, out, err = run_git(["worktree", "list", "--porcelain"], repo_root)
    if code != 0:
        return tool_result(False, action="list", error=(err or out).strip(), returncode=code)

    worktrees: list[dict] = []
    current: dict = {}
    for line in out.splitlines():
        line = line.rstrip()
        if not line:
            if current:
                worktrees.append(current)
                current = {}
            continue
        if line.startswith("worktree "):
            current = {"path": normalize_path(line[len("worktree "):])}
        elif line.startswith("HEAD "):
            current["head"] = line[len("HEAD "):]
        elif line.startswith("branch "):
            ref = line[len("branch "):]
            current["branch"] = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref
        elif line == "detached":
            current["detached"] = True
        elif line == "bare":
            current["bare"] = True
    if current:
        worktrees.append(current)
    return tool_result(True, action="list", worktrees=worktrees, count=len(worktrees), returncode=code)


def worktree_remove(repo_root: Path, path: str, delete_branch: bool = False, force: bool = False) -> dict:
    ok, msg = ensure_git_repo(repo_root)
    if not ok:
        return tool_result(False, action="remove", error=msg)

    branch = None
    if delete_branch:
        listing = worktree_list(repo_root)
        target = Path(path)
        for entry in listing.get("worktrees", []):
            try:
                if Path(entry["path"]).resolve() == target.resolve():
                    branch = entry.get("branch")
                    break
            except OSError:
                continue

    cmd = ["worktree", "remove"]
    if force:
        cmd.append("--force")
    cmd.append(str(path))
    code, out, err = run_git(cmd, repo_root)
    if code != 0:
        return tool_result(False, action="remove", error=(err or out).strip(), returncode=code)

    deleted_branch = None
    if delete_branch and branch:
        bcode, _, _ = run_git(["branch", "-D", branch], repo_root)
        deleted_branch = branch if bcode == 0 else None
    return tool_result(True, action="remove", removed=normalize_path(str(path)), deleted_branch=deleted_branch)


def plan_from_ownership(
    ownership_path: str | Path,
    repo_root: str | Path | None = None,
    create: bool = False,
    base_ref: str | None = None,
    worktrees_root: str | Path | None = None,
    force: bool = False,
) -> dict:
    path = Path(ownership_path)
    if not path.is_file():
        return tool_result(False, action="plan", error=f"ownership.json not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return tool_result(False, action="plan", error=f"invalid ownership.json: {exc}")

    root = resolve_repo_root(repo_root or data.get("workspace_root") or data.get("target_repo"))
    wt_root = worktrees_root_for(root, worktrees_root)

    plans: list[dict] = []
    created: list[dict] = []
    for task in data.get("tasks", []):
        if task.get("role") != "Worker":
            continue
        if task.get("write_permission") is False:
            continue
        branch = branch_for(task.get("task_id", "task"), task.get("session_name"))
        plans.append(
            {
                "task_id": task.get("task_id"),
                "session_name": task.get("session_name"),
                "role": task.get("role"),
                "branch": branch,
                "worktree_path": str(wt_root / branch.replace("/", "-")),
                "allowed_paths": task.get("allowed_paths", []),
            }
        )
        if create:
            created.append(
                worktree_create(
                    root,
                    task.get("task_id", "task"),
                    task.get("session_name"),
                    branch=branch,
                    base_ref=base_ref,
                    worktrees_root=worktrees_root,
                    force=force,
                )
            )

    result = tool_result(
        True,
        action="plan",
        repo_root=str(root),
        worktrees_root=str(wt_root),
        worker_count=len(plans),
        plans=plans,
    )
    if create:
        result["created"] = created
        result["ok"] = all(item.get("ok") for item in created) if created else True
    return result


def invoke(payload: dict) -> dict:
    action = payload.get("action", "list")
    if action == "plan":
        return plan_from_ownership(
            payload.get("ownership"),
            repo_root=payload.get("repo_root"),
            create=bool(payload.get("create")),
            base_ref=payload.get("base_ref"),
            worktrees_root=payload.get("worktrees_root"),
            force=bool(payload.get("force")),
        )

    repo_root = resolve_repo_root(payload.get("repo_root"))
    if action == "create":
        return worktree_create(
            repo_root,
            payload.get("task_id", "task"),
            payload.get("session_name"),
            branch=payload.get("branch"),
            base_ref=payload.get("base_ref"),
            worktrees_root=payload.get("worktrees_root"),
            setup=payload.get("setup"),
            force=bool(payload.get("force")),
        )
    if action == "list":
        return worktree_list(repo_root)
    if action == "remove":
        if not payload.get("path"):
            return tool_result(False, action="remove", error="remove requires 'path'")
        return worktree_remove(
            repo_root,
            payload["path"],
            delete_branch=bool(payload.get("delete_branch")),
            force=bool(payload.get("force")),
        )
    return tool_result(False, error=f"unknown action: {action}")


def run_self_check() -> int:
    if not shutil.which("git"):
        emit_json({"ok": True, "skipped": True, "message": "git not available; worktree_tool self-check skipped"})
        return 0

    errors: list[str] = []
    base = Path(tempfile.mkdtemp(prefix="worktree-tool-selfcheck-"))
    try:
        repo = base / "repo"
        repo.mkdir()
        for args in (
            ["init"],
            ["-c", "user.email=sc@example.com", "-c", "user.name=selfcheck", "commit", "--allow-empty", "-m", "init"],
        ):
            code, out, err = run_git(args, repo)
            if code != 0:
                errors.append(f"git {' '.join(args)} failed: {(err or out).strip()}")

        if not errors:
            created = worktree_create(repo, "T002", "worker-backend")
            if not created.get("ok"):
                errors.append(f"create failed: {created.get('error')}")
            else:
                if not Path(created["worktree_path"]).is_dir():
                    errors.append("worktree directory missing after create")
                listing = worktree_list(repo)
                if not listing.get("ok") or not any(
                    "T002" in (e.get("branch") or "") for e in listing.get("worktrees", [])
                ):
                    errors.append("created worktree not present in list output")
                dup = worktree_create(repo, "T002", "worker-backend")
                if dup.get("ok"):
                    errors.append("duplicate create without force should fail")
                removed = worktree_remove(repo, created["worktree_path"], delete_branch=True, force=True)
                if not removed.get("ok"):
                    errors.append(f"remove failed: {removed.get('error')}")
                elif removed.get("deleted_branch") != created["branch"]:
                    errors.append("remove did not delete the worktree branch")

        ownership = {
            "workspace_root": str(repo),
            "tasks": [
                {"task_id": "T001", "session_name": "explorer-x", "role": "Explorer", "write_permission": False, "allowed_paths": ["x/**"]},
                {"task_id": "T002", "session_name": "worker-backend", "role": "Worker", "write_permission": True, "allowed_paths": ["backend/**"]},
                {"task_id": "T003", "session_name": "worker-frontend", "role": "Worker", "write_permission": True, "allowed_paths": ["frontend/**"]},
                {"task_id": "T004", "session_name": "reviewer", "role": "Reviewer", "write_permission": False, "allowed_paths": ["**/*"]},
            ],
        }
        ownership_path = base / "ownership.json"
        ownership_path.write_text(json.dumps(ownership), encoding="utf-8")

        plan = plan_from_ownership(ownership_path, create=False)
        if not plan.get("ok") or plan.get("worker_count") != 2:
            errors.append(f"plan should map exactly 2 Workers, got {plan.get('worker_count')}")
        if len({p["branch"] for p in plan.get("plans", [])}) != 2:
            errors.append("plan Worker branches must be distinct")
        if any(p["role"] != "Worker" for p in plan.get("plans", [])):
            errors.append("plan must only include Workers")

        plan_created = plan_from_ownership(ownership_path, create=True)
        if not plan_created.get("ok") or not plan_created.get("created"):
            errors.append("plan --create should create worktrees")
        for entry in plan_created.get("created", []) or []:
            if not entry.get("ok"):
                errors.append(f"plan create entry failed: {entry.get('error')}")
            elif entry.get("worktree_path"):
                worktree_remove(repo, entry["worktree_path"], delete_branch=True, force=True)

        if not invoke({"action": "list", "repo_root": str(repo)}).get("ok"):
            errors.append("invoke(list) failed")
        bad = invoke({"action": "remove", "repo_root": str(repo)})
        if bad.get("ok"):
            errors.append("remove without path should fail")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    if errors:
        emit_json({"ok": False, "errors": errors})
        return 1
    emit_json({"ok": True, "message": "worktree_tool self-check passed"})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--action", choices=("create", "list", "remove", "plan"), default="list")
    parser.add_argument("--repo-root", help="Repository root (default: cwd, or ownership.workspace_root for plan)")
    parser.add_argument("--task-id", help="Task id for create")
    parser.add_argument("--session-name", help="Session/worker name for create")
    parser.add_argument("--branch", help="Explicit branch name (default: multi-agent/<task>-<session>)")
    parser.add_argument("--base-ref", help="Base ref/commit for the new branch (default: current HEAD)")
    parser.add_argument("--worktrees-root", help="Where to place worktrees (default: <repo>.worktrees sibling)")
    parser.add_argument("--setup", help="Optional shell command to run inside the new worktree")
    parser.add_argument("--ownership", help="Path to ownership.json (for --action plan)")
    parser.add_argument("--create", action="store_true", help="plan: actually create the planned worktrees")
    parser.add_argument("--path", help="Worktree path (for --action remove)")
    parser.add_argument("--delete-branch", action="store_true", help="remove: also delete the worktree branch")
    parser.add_argument("--force", action="store_true", help="Force create/remove")
    parser.add_argument("--json-in", help="JSON input string (otherwise stdin or flags)")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    # Prefer explicit flags. Only read JSON from stdin when no flags were given
    # and stdin is actually piped, so flag-based use from a non-TTY subprocess
    # (the common Main-agent case) never blocks waiting on stdin.
    flags_provided = any(
        [
            args.action != "list",
            args.repo_root,
            args.task_id,
            args.session_name,
            args.branch,
            args.base_ref,
            args.worktrees_root,
            args.setup,
            args.ownership,
            args.create,
            args.path,
            args.delete_branch,
            args.force,
        ]
    )

    if args.json_in is not None:
        result = invoke(load_json_input(args.json_in))
    elif not flags_provided and not sys.stdin.isatty():
        result = invoke(load_json_input(None))
    else:
        result = invoke(
            {
                "action": args.action,
                "repo_root": args.repo_root,
                "task_id": args.task_id,
                "session_name": args.session_name,
                "branch": args.branch,
                "base_ref": args.base_ref,
                "worktrees_root": args.worktrees_root,
                "setup": args.setup,
                "ownership": args.ownership,
                "create": args.create,
                "path": args.path,
                "delete_branch": args.delete_branch,
                "force": args.force,
            }
        )
    emit_json(result)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
