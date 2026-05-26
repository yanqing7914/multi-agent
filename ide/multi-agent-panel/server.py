#!/usr/bin/env python3
"""Read-only mission-control panel for .codex-multi-agent/ state (stdlib HTTP)."""

from __future__ import annotations

import argparse
import json
import mimetypes
import subprocess
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OPENCLAW_SCRIPTS = REPO_ROOT / "adapters" / "openclaw" / "scripts"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict | list:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_state_bundle(state_dir: Path) -> dict:
    status = read_json(state_dir / "status.json")
    ownership = read_json(state_dir / "ownership.json")
    findings_doc = read_json(state_dir / "findings" / "review-findings.json")
    findings = findings_doc.get("findings", []) if isinstance(findings_doc, dict) else []
    summary_md = read_text(state_dir / "summary" / "run-summary.md")

    latest_audit: dict = {}
    audits_dir = state_dir / "audits"
    if audits_dir.exists():
        audit_files = sorted(audits_dir.glob("audit-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if audit_files:
            latest_audit = read_json(audit_files[0])
            if isinstance(latest_audit, dict):
                latest_audit["audit_path"] = str(audit_files[0])

    if not latest_audit and isinstance(status, dict):
        latest_audit = status.get("latest_audit", {})

    tasks = []
    if isinstance(status, dict) and status.get("tasks"):
        for tid, entry in status["tasks"].items():
            task_entry = dict(entry)
            task_entry.setdefault("task_id", tid)
            preflight = entry.get("preflight")
            if preflight:
                task_entry["preflight_issues"] = [preflight.get("reason", str(preflight))]
            tasks.append(task_entry)
    elif isinstance(ownership, dict):
        for task in ownership.get("tasks", []):
            tasks.append(task)

    gates = status.get("gates", {}) if isinstance(status, dict) else {}

    return {
        "ok": True,
        "last_sync": utc_now(),
        "run": {
            "task_title": status.get("task_title") or ownership.get("task", ""),
            "run_id": status.get("run_id", ""),
            "current_phase": status.get("current_phase", ""),
            "workspace_root": status.get("workspace_root") or ownership.get("workspace_root", ""),
            "state_dir": str(state_dir),
            "updated_at": status.get("updated_at", ""),
        },
        "gates": gates,
        "tasks": tasks,
        "findings": findings,
        "latest_audit": latest_audit,
        "preflight_issues": status.get("preflight_issues", []) if isinstance(status, dict) else [],
        "summary_preview": summary_md,
    }


class PanelHandler(BaseHTTPRequestHandler):
    state_dir: Path = Path(".codex-multi-agent")
    write_enabled: bool = False
    refresh_seconds: int = 5

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(404)
            return
        content = path.read_bytes()
        mime, _ = mimetypes.guess_type(str(path))
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/api/state":
            self._send_json(200, load_state_bundle(self.state_dir))
            return

        if route == "/api/findings":
            doc = read_json(self.state_dir / "findings" / "review-findings.json")
            self._send_json(200, {"ok": True, "findings": doc.get("findings", []) if isinstance(doc, dict) else []})
            return

        if route == "/api/config":
            self._send_json(
                200,
                {
                    "refresh_seconds": self.refresh_seconds,
                    "write_enabled": self.write_enabled,
                    "state_dir": str(self.state_dir),
                },
            )
            return

        if route in {"/", "/index.html"}:
            self._send_file(STATIC_DIR / "index.html")
            return

        static_path = STATIC_DIR / route.lstrip("/")
        if static_path.exists() and static_path.is_relative_to(STATIC_DIR):
            self._send_file(static_path)
            return

        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        if not self.write_enabled:
            self._send_json(403, {"ok": False, "error": "Write endpoints disabled. Restart with --write."})
            return

        parsed = urlparse(self.path)
        route = parsed.path
        script_map = {
            "/api/sync": ["update_task_status.py", "--state-dir", str(self.state_dir), "--sync"],
            "/api/summarize": ["update_task_status.py", "--state-dir", str(self.state_dir), "--summarize"],
            "/api/audit": [
                "audit_worker_output.py",
                "--ownership", str(self.state_dir / "ownership.json"),
                "--results", str(self.state_dir / "results"),
                "--changed-files", str(self.state_dir / "changed-files.txt"),
                "--write-audit",
                "--state-dir", str(self.state_dir),
            ],
        }

        if route not in script_map:
            self.send_error(404)
            return

        cmd = [sys.executable, str(OPENCLAW_SCRIPTS / script_map[route][0]), *script_map[route][1:]]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        text = (proc.stdout or proc.stderr or "").strip()
        try:
            payload = json.loads(text) if text else {"returncode": proc.returncode}
        except json.JSONDecodeError:
            payload = {"returncode": proc.returncode, "output": text}
        payload["ok"] = proc.returncode == 0
        self._send_json(200 if proc.returncode == 0 else 500, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=".codex-multi-agent", help="Mission control state directory")
    parser.add_argument("--port", type=int, default=9876, help="HTTP port (default 9876)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default 127.0.0.1)")
    parser.add_argument("--write", action="store_true", help="Enable POST /api/sync, /api/audit, /api/summarize")
    parser.add_argument("--refresh", type=int, default=5, help="Default UI poll interval seconds")
    args = parser.parse_args()

    state_dir = Path(args.state_dir).expanduser().resolve()
    state_dir.mkdir(parents=True, exist_ok=True)

    PanelHandler.state_dir = state_dir
    PanelHandler.write_enabled = args.write
    PanelHandler.refresh_seconds = args.refresh

    server = ThreadingHTTPServer((args.host, args.port), PanelHandler)
    print(
        json.dumps(
            {
                "ok": True,
                "url": f"http://{args.host}:{args.port}/",
                "state_dir": str(state_dir),
                "write_enabled": args.write,
            },
            indent=2,
        ),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
