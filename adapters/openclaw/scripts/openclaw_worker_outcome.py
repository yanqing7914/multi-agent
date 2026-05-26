#!/usr/bin/env python3
"""OpenClaw session log → normalized worker outcome (dependency-free)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SHARED = Path(__file__).resolve().parent.parent.parent / "_shared"
sys.path.insert(0, str(SHARED))

from worker_outcome import (  # noqa: E402
    detect_log_error_mode,
    map_runtime_log_to_normalized,
    normalize_error_code,
)


def evaluate_openclaw_log(log_text: str) -> dict:
    code = map_runtime_log_to_normalized(log_text, runtime="openclaw")
    return {
        "ok": code is None,
        "runtime": "openclaw",
        "normalized_error": normalize_error_code(code),
        "raw_mode": code,
    }


def run_self_check() -> int:
    errors: list[str] = []
    fixtures = SHARED / "fixtures"
    for name, expected in {
        "timeout.log": "timeout",
        "openclaw_acp_timeout.log": "timeout",
    }.items():
        path = fixtures / name
        if not path.exists():
            errors.append(f"missing fixture {name}")
            continue
        payload = evaluate_openclaw_log(path.read_text(encoding="utf-8"))
        if payload.get("normalized_error") != expected:
            errors.append(f"{name}: expected {expected}, got {payload}")

    sample = evaluate_openclaw_log("session completed\n")
    if not sample.get("ok"):
        errors.append("clean openclaw log should be ok")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "openclaw outcome self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-log", help="Evaluate a session log file")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    if args.fixture_log:
        text = Path(args.fixture_log).read_text(encoding="utf-8")
        print(json.dumps(evaluate_openclaw_log(text), indent=2))
        return 0

    parser.error("Specify --self-check or --fixture-log")


if __name__ == "__main__":
    raise SystemExit(main())
