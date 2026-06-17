#!/usr/bin/env python3
"""Verify workspace_root exists and required_paths are reachable (dependency-free)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _preflight import verify_required_paths


def run_self_check() -> int:
    root = Path(__file__).resolve().parent.parent.parent.parent
    required = "adapters/openclaw" if (root / "adapters" / "openclaw").exists() else "."
    checked, missing = verify_required_paths(root, [required])
    if missing:
        print(json.dumps({"ok": False, "errors": [f"missing: {missing}"]}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "verify_workspace self-check passed", "checked": checked}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true", help="Run built-in validation and exit")
    parser.add_argument("--workspace-root", help="Absolute path to target repo")
    parser.add_argument("--required-paths", nargs="*", default=[], help="Glob patterns from task card")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human lines")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    if not args.workspace_root:
        parser.error("--workspace-root is required unless --self-check is used")

    root = Path(args.workspace_root).resolve()
    if not root.is_dir():
        payload = {"ok": False, "error": f"workspace_root is not a directory: {root}"}
        print(json.dumps(payload, indent=2))
        return 1

    checked, missing = verify_required_paths(root, args.required_paths)
    ok = not missing
    payload = {
        "ok": ok,
        "workspace_root": str(root),
        "required_paths_checked": checked,
        "required_paths_missing": missing,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"workspace_root: {root}")
        print(f"pwd equivalent: {root}")
        for item in checked:
            status = "ok" if item not in missing else "MISSING"
            print(f"  [{status}] {item}")
        if missing:
            print("FAIL: required paths missing — subagent must cd to workspace_root first", file=sys.stderr)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
