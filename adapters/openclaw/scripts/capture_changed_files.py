#!/usr/bin/env python3
"""Capture the full set of changed files (staged + unstaged + untracked) for scope audit.

`git diff --name-only` alone misses untracked files, which lets a Worker create
new files outside `allowed_paths` without the audit ever seeing them. This
helper writes the union of staged, unstaged, and untracked paths to
`<state-dir>/changed-files.txt`, excluding the mission-control state directory
itself.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath


def git_lines(args: list[str], cwd: Path) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}")
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def collect_changed_files(workspace_root: Path, exclude_prefixes: list[str]) -> list[str]:
    seen: set[str] = set()
    for args in (
        ["diff", "--name-only"],
        ["diff", "--name-only", "--cached"],
        ["ls-files", "--others", "--exclude-standard"],
    ):
        seen.update(git_lines(args, workspace_root))
    results = []
    for name in sorted(seen):
        posix = PurePosixPath(name)
        if any(posix == PurePosixPath(p) or str(posix).startswith(p.rstrip("/") + "/") for p in exclude_prefixes):
            continue
        results.append(name)
    return results


def capture(workspace_root: Path, state_dir: Path, output: Path | None = None) -> dict:
    workspace_root = workspace_root.resolve()
    state_dir = state_dir.resolve()
    exclude: list[str] = []
    try:
        exclude.append(state_dir.relative_to(workspace_root).as_posix())
    except ValueError:
        pass
    changed = collect_changed_files(workspace_root, exclude)
    target = output or (state_dir / "changed-files.txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(changed) + ("\n" if changed else ""), encoding="utf-8")
    return {
        "ok": True,
        "workspace_root": str(workspace_root),
        "changed_files": changed,
        "count": len(changed),
        "output": str(target),
    }


def run_self_check() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="capture-changed-files-") as tmp:
        root = Path(tmp)
        run = lambda *args: subprocess.run(  # noqa: E731
            ["git", *args], cwd=root, capture_output=True, text=True, check=False
        )
        run("init", "-q")
        run("config", "user.email", "self-check@example.com")
        run("config", "user.name", "self-check")
        (root / "src").mkdir()
        (root / "src" / "tracked.py").write_text("x = 1\n", encoding="utf-8")
        run("add", "-A")
        run("commit", "-q", "-m", "init")

        (root / "src" / "tracked.py").write_text("x = 2\n", encoding="utf-8")
        (root / "sneaky.py").write_text("evil = True\n", encoding="utf-8")
        state_dir = root / ".codex-multi-agent"
        (state_dir / "results").mkdir(parents=True)
        (state_dir / "results" / "T001.json").write_text("{}", encoding="utf-8")

        payload = capture(root, state_dir)
        changed = payload["changed_files"]
        if "src/tracked.py" not in changed:
            errors.append("modified tracked file missing from capture")
        if "sneaky.py" not in changed:
            errors.append("untracked file missing from capture (audit blind spot)")
        if any(name.startswith(".codex-multi-agent") for name in changed):
            errors.append("state dir must be excluded from capture")
        listed = Path(payload["output"]).read_text(encoding="utf-8").splitlines()
        if sorted(listed) != sorted(changed):
            errors.append("changed-files.txt content mismatch")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "capture_changed_files self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", help="Target repo root (default: current directory)")
    parser.add_argument("--state-dir", default=".codex-multi-agent", help="Mission-control state directory")
    parser.add_argument("--output", help="Override output path (default: <state-dir>/changed-files.txt)")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    workspace_root = Path(args.workspace_root).resolve() if args.workspace_root else Path.cwd().resolve()
    state_dir = Path(args.state_dir)
    if not state_dir.is_absolute():
        state_dir = workspace_root / state_dir
    output = Path(args.output) if args.output else None
    try:
        payload = capture(workspace_root, state_dir, output)
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 1
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
