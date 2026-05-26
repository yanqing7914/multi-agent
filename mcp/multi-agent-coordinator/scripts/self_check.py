#!/usr/bin/env python3
"""In-process smoke test for multi-agent-coordinator MCP server."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SERVER = REPO_ROOT / "mcp" / "multi-agent-coordinator" / "server.py"


class PipeClient:
  """Send JSON-RPC requests to server subprocess over stdin/stdout."""

  def __init__(self, state_dir: Path) -> None:
    self.proc = subprocess.Popen(
      [sys.executable, str(SERVER), "--state-dir", str(state_dir)],
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      text=True,
      bufsize=1,
    )
    self._lock = threading.Lock()
    self._id = 0

  def request(self, method: str, params: dict | None = None) -> dict:
    with self._lock:
      self._id += 1
      msg_id = self._id
      payload = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}}
      assert self.proc.stdin is not None
      assert self.proc.stdout is not None
      self.proc.stdin.write(json.dumps(payload) + "\n")
      self.proc.stdin.flush()
      while True:
        line = self.proc.stdout.readline()
        if not line:
          raise RuntimeError("server closed stdout")
        response = json.loads(line)
        if response.get("id") == msg_id:
          if "error" in response:
            raise RuntimeError(json.dumps(response["error"]))
          return response.get("result", {})

  def notify(self, method: str, params: dict | None = None) -> None:
    with self._lock:
      payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
      assert self.proc.stdin is not None
      self.proc.stdin.write(json.dumps(payload) + "\n")
      self.proc.stdin.flush()

  def close(self) -> None:
    if self.proc.stdin:
      self.proc.stdin.close()
    self.proc.wait(timeout=5)


def call_tool(client: PipeClient, name: str, arguments: dict) -> dict:
  result = client.request("tools/call", {"name": name, "arguments": arguments})
  text = result["content"][0]["text"]
  return json.loads(text)


def run_self_check() -> int:
  errors: list[str] = []
  with tempfile.TemporaryDirectory(prefix="mcp-coordinator-") as tmp:
    state_dir = Path(tmp) / ".codex-multi-agent"
    state_dir.mkdir()
    workspace = Path(tmp) / "workspace"
    workspace.mkdir()

    client = PipeClient(state_dir)
    try:
      init = client.request(
        "initialize",
        {
          "protocolVersion": "2024-11-05",
          "capabilities": {},
          "clientInfo": {"name": "self_check", "version": "1.0"},
        },
      )
      if init.get("serverInfo", {}).get("name") != "multi-agent-coordinator":
        errors.append("initialize missing serverInfo")

      client.notify("notifications/initialized")

      tools = client.request("tools/list", {})
      tool_names = {t["name"] for t in tools.get("tools", [])}
      required = {
        "create_task", "list_tasks", "update_task_status", "record_finding",
        "summarize_review", "audit_scope", "generate_final_report", "list_framework_tools",
      }
      missing = required - tool_names
      if missing:
        errors.append(f"tools/list missing: {sorted(missing)}")

      created = call_tool(
        client,
        "create_task",
        {
          "workspace": str(workspace),
          "task": {
            "id": "T001",
            "role": "Explorer",
            "mode": "research",
            "title": "Explore backend",
            "objective": "Map backend layout",
            "allowed_paths": ["backend/**"],
            "session_name": "explorer-backend",
          },
        },
      )
      if not created.get("ok"):
        errors.append(f"create_task failed: {created}")

      call_tool(
        client,
        "create_task",
        {
          "workspace": str(workspace),
          "task": {
            "id": "T002",
            "role": "Worker",
            "mode": "implement",
            "title": "Implement backend",
            "objective": "Add feature",
            "allowed_paths": ["backend/**"],
            "session_name": "worker-backend",
          },
        },
      )

      listed = call_tool(client, "list_tasks", {"workspace": str(workspace)})
      if listed.get("count", 0) < 2:
        errors.append("list_tasks expected >= 2 tasks")

      updated = call_tool(
        client,
        "update_task_status",
        {"workspace": str(workspace), "task_id": "T001", "status": "running", "note": "spawned"},
      )
      if not updated.get("ok"):
        errors.append(f"update_task_status failed: {updated}")

      call_tool(
        client,
        "record_result",
        {
          "workspace": str(workspace),
          "result": {
            "task_id": "T001",
            "session_name": "explorer-backend",
            "role": "Explorer",
            "status": "completed",
            "summary": "Explored backend",
            "files_read": ["backend/app.py"],
            "files_changed": [],
            "required_paths_verified": True,
          },
        },
      )

      finding = call_tool(
        client,
        "record_finding",
        {
          "workspace": str(workspace),
          "finding": {
            "reviewer_task_id": "T003",
            "severity": "P2",
            "title": "Self-check finding",
            "target_file": "backend/app.py",
            "line": 1,
            "evidence": "test",
            "recommendation": "fix",
          },
        },
      )
      if not finding.get("ok"):
        errors.append(f"record_finding failed: {finding}")

      tools = call_tool(client, "list_framework_tools", {})
      if tools.get("count", 0) < 5:
        errors.append("list_framework_tools expected >= 5 tools")

      summary = call_tool(client, "summarize_review", {"workspace": str(workspace)})
      if summary.get("finding_count", 0) < 1:
        errors.append("summarize_review expected findings")

      call_tool(
        client,
        "record_finding",
        {
          "workspace": str(workspace),
          "finding": {
            "reviewer_task_id": "T004",
            "severity": "P1",
            "title": "Self-check finding",
            "target_file": "backend/app.py",
            "line": 1,
            "evidence": "duplicate title different reviewer",
            "recommendation": "fix",
            "source": "reviewer-b",
          },
        },
      )
      dedup_summary = call_tool(client, "summarize_review", {"workspace": str(workspace), "group_duplicates": True})
      if dedup_summary.get("finding_count", 0) < 2:
        errors.append("duplicate-title-from-different-reviewers must remain distinct")

      (state_dir / "results" / "T002-worker-backend.json").write_text(
        json.dumps(
          {
            "task_id": "T002",
            "role": "Worker",
            "status": "completed",
            "files_changed": ["backend/app.py"],
          },
          indent=2,
        ),
        encoding="utf-8",
      )
      (state_dir / "changed-files.txt").write_text("backend/app.py\n", encoding="utf-8")

      audit = call_tool(client, "audit_scope", {"workspace": str(workspace)})
      if "ok" not in audit:
        errors.append("audit_scope missing ok field")

      report = call_tool(client, "generate_final_report", {"workspace": str(workspace)})
      if not report.get("ok"):
        errors.append(f"generate_final_report failed: {report}")

      findings_doc = json.loads((state_dir / "findings" / "review-findings.json").read_text(encoding="utf-8"))
      if not any(item.get("title") == "Self-check finding" for item in findings_doc.get("findings", [])):
        errors.append("MCP finding must survive sync after generate_final_report")

      resources = client.request("resources/list", {})
      uris = {r["uri"] for r in resources.get("resources", [])}
      if "multi-agent://state" not in uris:
        errors.append("resources/list missing multi-agent://state")

      state_read = client.request("resources/read", {"uri": "multi-agent://state"})
      if not state_read.get("contents"):
        errors.append("resources/read state empty")

      prompts = client.request("prompts/list", {})
      if len(prompts.get("prompts", [])) < 4:
        errors.append("prompts/list expected >= 4 prompts")

      for path in (
        state_dir / "status.json",
        state_dir / "ownership.json",
        state_dir / "findings" / "review-findings.json",
        state_dir / "summary" / "run-summary.md",
      ):
        if not path.exists():
          errors.append(f"expected state file missing: {path}")

      if not list((state_dir / "audits").glob("audit-*.json")):
        errors.append("expected audit JSON under audits/")

      if not list((state_dir / "tasks").glob("*.md")):
        errors.append("expected task cards under tasks/")

    finally:
      client.close()

  if errors:
    print(json.dumps({"ok": False, "errors": errors}, indent=2))
    return 1
  print(json.dumps({"ok": True, "message": "multi-agent-coordinator MCP self-check passed"}, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(run_self_check())
