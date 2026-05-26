#!/usr/bin/env python3
"""IDE layer self-check: panel + extension scaffolds."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PANEL_SELF_CHECK = REPO_ROOT / "ide" / "multi-agent-panel" / "scripts" / "self_check.py"
EXTENSION_ROOTS = [
    REPO_ROOT / "ide" / "extensions" / "vscode",
    REPO_ROOT / "ide" / "extensions" / "cursor",
    REPO_ROOT / "ide" / "extensions" / "hermes",
]


def run_self_check() -> int:
    errors: list[str] = []

    if PANEL_SELF_CHECK.exists():
        proc = subprocess.run([sys.executable, str(PANEL_SELF_CHECK)], capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            errors.append(f"panel self-check failed: {(proc.stderr or proc.stdout)[:300]}")
    else:
        errors.append("panel self-check script missing")

    for root in EXTENSION_ROOTS:
        if not root.is_dir():
            errors.append(f"missing extension scaffold: {root.name}")
            continue
        readme = root / "README.md"
        if not readme.exists():
            errors.append(f"{root.name}: README.md missing")
        if root.name in {"vscode", "cursor"}:
            for name in ("package.json", "extension.ts"):
                if not (root / name).exists():
                    errors.append(f"{root.name}: {name} missing")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "ide self-check passed", "extensions": [p.name for p in EXTENSION_ROOTS]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_self_check())
