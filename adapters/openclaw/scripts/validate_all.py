#!/usr/bin/env python3
"""Run all OpenClaw adapter self-checks (dependency-free)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ADAPTER_ROOT = SCRIPT_DIR.parent

from _runtimes import runtime_consistency_self_check  # noqa: E402

FORBIDDEN_ADAPTER_ARTIFACTS = (
    ".tmp-openclaw-test",
    ".codex-multi-agent",
    ".codex-multi-agent-demo",
)


def check_adapter_artifacts() -> list[str]:
    """Fail if mission-control temp dirs were left inside the adapter package."""
    errors: list[str] = []
    for name in FORBIDDEN_ADAPTER_ARTIFACTS:
        path = ADAPTER_ROOT / name
        if path.exists():
            errors.append(f"remove generated artifact under adapter package: {path}")
    return errors


CHECKS = [
    ("create_task_cards", "create_task_cards.py"),
    ("update_task_status", "update_task_status.py"),
    ("audit_worker_output", "audit_worker_output.py"),
    ("verify_workspace", "verify_workspace.py"),
    ("run_local_demo", "run_local_demo.py"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = parser.parse_args()

    results: list[dict] = []
    errors: list[str] = []

    for name, script in CHECKS:
        path = SCRIPT_DIR / script
        proc = subprocess.run(
            [sys.executable, str(path), "--self-check"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        ok = proc.returncode == 0
        entry = {"name": name, "script": script, "ok": ok, "returncode": proc.returncode}
        if not ok:
            entry["stderr"] = (proc.stderr or proc.stdout or "").strip()[:500]
            errors.append(f"{name}: {entry.get('stderr', 'failed')}")
        results.append(entry)

    runtime_errors = runtime_consistency_self_check()
    results.append(
        {
            "name": "runtime_constants",
            "script": "_runtimes.py",
            "ok": not runtime_errors,
            "returncode": 0 if not runtime_errors else 1,
        }
    )
    if runtime_errors:
        errors.extend(runtime_errors)

    artifact_errors = check_adapter_artifacts()
    artifact_ok = not artifact_errors
    results.append({"name": "adapter_artifacts", "script": "(inline)", "ok": artifact_ok, "returncode": 0 if artifact_ok else 1})
    if artifact_errors:
        errors.extend(artifact_errors)

    payload = {"ok": not errors, "checks": results, "errors": errors}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for item in results:
            status = "PASS" if item["ok"] else "FAIL"
            print(f"[{status}] {item['name']}")
        if errors:
            print("\nFailures:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
