#!/usr/bin/env python3
"""Smoke test for ide/multi-agent-panel HTTP server."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PANEL_SERVER = REPO_ROOT / "ide" / "multi-agent-panel" / "server.py"
FIXTURE = REPO_ROOT / ".codex-multi-agent-real-dogfood"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_self_check() -> int:
    errors: list[str] = []
    port = free_port()

    with tempfile.TemporaryDirectory(prefix="panel-self-check-") as tmp:
        state_dir = Path(tmp) / ".codex-multi-agent"
        if FIXTURE.exists():
            shutil.copytree(FIXTURE, state_dir)
        else:
            state_dir.mkdir()
            (state_dir / "status.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "run_id": "test-run",
                        "task_title": "Panel self-check",
                        "current_phase": "explorers_complete",
                        "gates": {"explorers_complete": {"status": "pending"}},
                        "tasks": {},
                        "preflight_issues": [],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            (state_dir / "findings").mkdir()
            (state_dir / "findings" / "review-findings.json").write_text(
                json.dumps({"findings": []}, indent=2),
                encoding="utf-8",
            )

        proc = subprocess.Popen(
            [
                sys.executable,
                str(PANEL_SERVER),
                "--state-dir",
                str(state_dir),
                "--port",
                str(port),
                "--host",
                "127.0.0.1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(30):
                try:
                    fetch_json(f"{base}/api/state")
                    break
                except (urllib.error.URLError, ConnectionResetError):
                    time.sleep(0.2)
            else:
                errors.append("server did not become ready")
                stderr = proc.stderr.read() if proc.stderr else ""
                if stderr:
                    errors.append(stderr[:300])

            state = fetch_json(f"{base}/api/state")
            if not state.get("ok"):
                errors.append("/api/state ok=false")
            for key in ("run", "gates", "tasks", "findings", "latest_audit", "summary_preview"):
                if key not in state:
                    errors.append(f"/api/state missing key: {key}")

            findings = fetch_json(f"{base}/api/findings")
            if "findings" not in findings:
                errors.append("/api/findings missing findings key")

            index_resp = urllib.request.urlopen(f"{base}/", timeout=10)
            if b"Multi-Agent Mission Control" not in index_resp.read():
                errors.append("index.html missing expected title")

        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "multi-agent-panel self-check passed"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(run_self_check())
