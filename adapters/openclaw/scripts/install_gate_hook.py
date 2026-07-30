#!/usr/bin/env python3
"""Install a git pre-commit hook that blocks secret/blocked paths (stdlib only).

The scope audit and gated_merge run at *delivery* time. This hook adds a second,
earlier line of defence at *commit* time: any staged file matching a secret or
blocked path is rejected before it can enter history — in any Worker worktree or
the main tree. It reuses the exact matching logic from tools/_tool_base.py, so
the hook and the audit agree on what counts as a secret.

Usage:
  python3 install_gate_hook.py --repo-root .            # install (idempotent)
  python3 install_gate_hook.py --repo-root . --check    # report install status
  python3 install_gate_hook.py --self-check             # built-in validation

The hook is a small self-contained Python script. It honours the standard
`git commit --no-verify` escape hatch (git skips all pre-commit hooks), so it is
a guardrail, not an inescapable lock — matching this project's honest framing.
"""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK_MARKER = "# multi-agent-coding:gate-hook:v1"

# The hook body is intentionally self-contained (no imports from this repo) so
# it keeps working after the skill tree is moved or uninstalled. It embeds the
# same default blocked/secret patterns as tools/_tool_base.py.
HOOK_TEMPLATE = '''#!/usr/bin/env python3
"""Reject commits that stage secret/blocked paths. Bypass with `git commit --no-verify`."""
{marker}
import fnmatch
import subprocess
import sys

BLOCKED = [
    ".env", ".env.*", ".npmrc", ".pypirc", ".netrc",
    "~/.ssh/**", "~/.codex/auth.json",
    "**/*.pem", "**/*.key", "**/*.p12", "**/*.pfx",
    "id_rsa", "id_ed25519", "**/credentials.json", "**/secrets/**",
]


def norm(p):
    p = p.replace("\\\\", "/").strip()
    while p.startswith("./"):
        p = p[2:]
    return p


def seg_match(path, pattern):
    if pattern == "**":
        return True
    if pattern.startswith("**/") and pattern.endswith("/**"):
        mid = pattern[3:-3]
        if not mid:
            return True
        for s in path.split("/"):
            if fnmatch.fnmatch(s, mid):
                return True
        return fnmatch.fnmatch(path.split("/")[-1], mid)
    if pattern.endswith("/**"):
        base = pattern[:-3]
        return path == base or path.startswith(base + "/")
    if pattern.startswith("**/"):
        suffix = pattern[3:]
        if fnmatch.fnmatch(path, suffix):
            return True
        for i in range(path.count("/") + 1):
            if fnmatch.fnmatch("/".join(path.split("/")[i:]), suffix):
                return True
        return False
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(path.split("/")[-1], pattern)


def blocked(path):
    path = norm(path)
    import os
    abs_path = norm(os.path.expanduser(path))
    for pat in BLOCKED:
        pat = norm(pat)
        if pat.startswith("~/"):
            exp = norm(os.path.expanduser(pat))
            rem = pat[2:]
            if seg_match(abs_path, exp) or seg_match(path, exp) or seg_match(path, rem):
                return True
            continue
        if seg_match(path, pat) or seg_match(abs_path, pat):
            return True
    return False


def main():
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True,
    ).stdout
    staged = [l.strip() for l in out.splitlines() if l.strip()]
    hits = [p for p in staged if blocked(p)]
    if hits:
        sys.stderr.write(
            "\\n[multi-agent gate] commit blocked: staged files match secret/blocked paths:\\n"
        )
        for h in hits:
            sys.stderr.write(f"  - {{h}}\\n")
        sys.stderr.write(
            "Remove them from the index (git restore --staged <file>) or, if intentional,\\n"
            "bypass with: git commit --no-verify\\n\\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def hooks_dir(repo_root: Path) -> tuple[Path | None, str]:
    proc = subprocess.run(
        ["git", "rev-parse", "--git-path", "hooks"],
        cwd=str(repo_root), capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None, f"not a git repo: {proc.stderr.strip()}"
    return (repo_root / proc.stdout.strip()).resolve(), ""


def hook_body() -> str:
    return HOOK_TEMPLATE.format(marker=HOOK_MARKER)


def is_our_hook(path: Path) -> bool:
    try:
        return HOOK_MARKER in path.read_text(encoding="utf-8")
    except OSError:
        return False


def install(repo_root: Path, force: bool = False) -> dict:
    hdir, err = hooks_dir(repo_root)
    if err:
        return {"ok": False, "error": err}
    hdir.mkdir(parents=True, exist_ok=True)
    hook_path = hdir / "pre-commit"

    if hook_path.exists() and not is_our_hook(hook_path) and not force:
        return {
            "ok": False,
            "installed": False,
            "hook_path": str(hook_path),
            "error": "a different pre-commit hook already exists; re-run with --force to replace it",
        }

    hook_path.write_text(hook_body(), encoding="utf-8")
    mode = hook_path.stat().st_mode
    hook_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return {"ok": True, "installed": True, "hook_path": str(hook_path)}


def check(repo_root: Path) -> dict:
    hdir, err = hooks_dir(repo_root)
    if err:
        return {"ok": False, "error": err}
    hook_path = hdir / "pre-commit"
    if not hook_path.exists():
        return {"ok": False, "installed": False, "hook_path": str(hook_path), "note": "no pre-commit hook"}
    ours = is_our_hook(hook_path)
    executable = bool(hook_path.stat().st_mode & stat.S_IXUSR)
    return {
        "ok": ours and executable,
        "installed": ours,
        "executable": executable,
        "hook_path": str(hook_path),
    }


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def run_self_check() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="gate-hook-selfcheck-") as tmp:
        root = Path(tmp)
        _git(["init", "-q", "-b", "main"], root)
        _git(["config", "user.email", "h@l"], root)
        _git(["config", "user.name", "h"], root)

        res = install(root)
        if not res.get("installed"):
            errors.append(f"install failed: {res}")
        chk = check(root)
        if not chk.get("ok"):
            errors.append(f"check should be ok after install: {chk}")

        # A normal file must commit fine.
        (root / "ok.py").write_text("x = 1\n", encoding="utf-8")
        _git(["add", "-A"], root)
        good = _git(["commit", "-m", "normal"], root)
        if good.returncode != 0:
            errors.append(f"normal commit should succeed, got: {good.stderr.strip()}")

        # A secret path must be rejected by the hook.
        secret = root / "src" / "secrets" / "keys.json"
        secret.parent.mkdir(parents=True, exist_ok=True)
        secret.write_text('{"k":"v"}\n', encoding="utf-8")
        (root / "src" / "app.py").write_text("y = 2\n", encoding="utf-8")
        _git(["add", "-A"], root)
        blocked_commit = _git(["commit", "-m", "sneak secret"], root)
        if blocked_commit.returncode == 0:
            errors.append("commit with src/secrets/keys.json should be BLOCKED by hook but succeeded")

        # --no-verify must still let it through (honest guardrail, not a lock).
        bypass = _git(["commit", "--no-verify", "-m", "bypass"], root)
        if bypass.returncode != 0:
            errors.append(f"--no-verify should bypass the hook, got: {bypass.stderr.strip()}")

        # A .env at repo root must also be blocked.
        _git(["checkout", "-q", "-b", "envtest"], root)
        (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
        _git(["add", "-A", "-f"], root)
        env_commit = _git(["commit", "-m", "add env"], root)
        if env_commit.returncode == 0:
            errors.append(".env commit should be blocked by hook but succeeded")

    if errors:
        print("install_gate_hook self-check FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("install_gate_hook self-check OK (blocks secrets/.env at commit, allows normal, honours --no-verify)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="Run built-in validation and exit")
    parser.add_argument("--repo-root", default=".", help="Repository root (default: cwd)")
    parser.add_argument("--check", action="store_true", help="Report install status without changing anything")
    parser.add_argument("--force", action="store_true", help="Replace an existing non-gate pre-commit hook")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    repo_root = Path(args.repo_root).expanduser().resolve()
    if args.check:
        import json
        result = check(repo_root)
        print(json.dumps(result, indent=2))
        return 0 if result.get("ok") else 1

    import json
    result = install(repo_root, force=args.force)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
