#!/usr/bin/env python3
"""Smoke test for the multi-agent-coordinator MCP server.

Two complementary phases, both dependency-free and driven against a throwaway
temp state dir:

* **in-process** — import ``server`` and drive ``MCPServer.handle`` directly
  (no child process). It dynamically reads ``server.TOOLS`` / ``server.RESOURCES``
  / ``server.PROMPTS`` and asserts the live ``tools/list`` / ``resources/list`` /
  ``prompts/list`` match them exactly (count + names), then smoke-calls **every**
  advertised tool. A newly added tool therefore cannot ship without coverage here.
* **cross-process** — spawn ``server.py`` over stdio and replay a minimal
  JSON-RPC handshake so transport-level framing stays covered.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

COORD_DIR = Path(__file__).resolve().parent.parent
SERVER = COORD_DIR / "server.py"

if str(COORD_DIR) not in sys.path:
  sys.path.insert(0, str(COORD_DIR))

import server as server_mod  # noqa: E402  in-process import (also wires coordinator paths)

# Advertised surface, read dynamically from the server module.
ADVERTISED_TOOLS = {tool["name"] for tool in server_mod.TOOLS}
ADVERTISED_RESOURCES = {res["uri"] for res in server_mod.RESOURCES}
ADVERTISED_PROMPTS = set(server_mod.PROMPTS)

# The full contract the server is expected to expose. Kept explicit so a
# tool/resource added (or removed) in server.py trips this check until the
# smoke coverage below is updated to match.
EXPECTED_TOOLS = {
  "list_framework_tools",
  "create_task",
  "list_tasks",
  "get_task",
  "update_task_status",
  "record_result",
  "check_path_allowed",
  "record_touched_paths",
  "request_skill_use",
  "approve_skill_use",
  "record_finding",
  "summarize_review",
  "audit_scope",
  "generate_final_report",
  "plan_worktrees",
  "check_readiness",
}
EXPECTED_RESOURCES = {
  "multi-agent://state",
  "multi-agent://tasks",
  "multi-agent://findings",
  "multi-agent://approvals",
}
EXPECTED_PROMPTS = {
  "create_worker_task_card",
  "create_review_agents_with_ssrd",
  "summarize_multi_agent_results",
  "audit_before_final_delivery",
}

INIT_PARAMS = {
  "protocolVersion": "2024-11-05",
  "capabilities": {},
  "clientInfo": {"name": "self_check", "version": "1.0"},
}


class InProcessClient:
  """Drive MCPServer.handle() directly — no child process, no stdin loop."""

  def __init__(self, state_dir: Path) -> None:
    self.server = server_mod.MCPServer(state_dir)
    self._id = 0

  def request(self, method: str, params: dict | None = None) -> dict:
    self._id += 1
    message = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
    response = self.server.handle(message)
    if response is None:
      raise RuntimeError(f"no response for {method}")
    if "error" in response:
      raise RuntimeError(json.dumps(response["error"]))
    return response.get("result", {})

  def notify(self, method: str, params: dict | None = None) -> None:
    self.server.handle({"jsonrpc": "2.0", "method": method, "params": params or {}})

  def close(self) -> None:
    return None


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


def call_tool(client, name: str, arguments: dict) -> dict:
  result = client.request("tools/call", {"name": name, "arguments": arguments})
  text = result["content"][0]["text"]
  return json.loads(text)


def initialize(client) -> dict:
  init = client.request("initialize", INIT_PARAMS)
  client.notify("notifications/initialized")
  return init


def assert_surface(client, errors: list[str], *, scope: str) -> None:
  """Assert the live tools/resources/prompts lists match the module surface."""
  tools = client.request("tools/list", {})
  tool_names = {tool["name"] for tool in tools.get("tools", [])}
  if len(tools.get("tools", [])) != len(server_mod.TOOLS):
    errors.append(f"[{scope}] tools/list count {len(tools.get('tools', []))} != server.TOOLS {len(server_mod.TOOLS)}")
  if tool_names != ADVERTISED_TOOLS:
    errors.append(f"[{scope}] tools/list names {sorted(tool_names)} != server.TOOLS {sorted(ADVERTISED_TOOLS)}")
  missing_key = EXPECTED_TOOLS - tool_names
  if missing_key:
    errors.append(f"[{scope}] tools/list missing key tools: {sorted(missing_key)}")

  resources = client.request("resources/list", {})
  uris = {res["uri"] for res in resources.get("resources", [])}
  if len(resources.get("resources", [])) != len(server_mod.RESOURCES):
    errors.append(f"[{scope}] resources/list count {len(resources.get('resources', []))} != server.RESOURCES {len(server_mod.RESOURCES)}")
  if uris != ADVERTISED_RESOURCES:
    errors.append(f"[{scope}] resources/list {sorted(uris)} != server.RESOURCES {sorted(ADVERTISED_RESOURCES)}")
  if uris != EXPECTED_RESOURCES:
    errors.append(f"[{scope}] resources/list {sorted(uris)} != expected {sorted(EXPECTED_RESOURCES)}")

  prompts = client.request("prompts/list", {})
  prompt_names = {prompt["name"] for prompt in prompts.get("prompts", [])}
  if len(prompts.get("prompts", [])) != len(server_mod.PROMPTS):
    errors.append(f"[{scope}] prompts/list count {len(prompts.get('prompts', []))} != server.PROMPTS {len(server_mod.PROMPTS)}")
  if prompt_names != ADVERTISED_PROMPTS:
    errors.append(f"[{scope}] prompts/list {sorted(prompt_names)} != server.PROMPTS {sorted(ADVERTISED_PROMPTS)}")
  if prompt_names != EXPECTED_PROMPTS:
    errors.append(f"[{scope}] prompts/list {sorted(prompt_names)} != expected {sorted(EXPECTED_PROMPTS)}")


def check_in_process(state_dir: Path, workspace: Path, errors: list[str]) -> None:
  """Drive every advertised tool in-process against a temp state dir."""
  client = InProcessClient(state_dir)
  called: set[str] = set()

  init = initialize(client)
  if init.get("serverInfo", {}).get("name") != "multi-agent-coordinator":
    errors.append("initialize missing serverInfo")
  if init.get("protocolVersion") != server_mod.PROTOCOL_VERSION:
    errors.append("initialize protocolVersion mismatch")

  assert_surface(client, errors, scope="in-process")

  framework = call_tool(client, "list_framework_tools", {})
  called.add("list_framework_tools")
  if framework.get("count", 0) < 5:
    errors.append("list_framework_tools expected >= 5 tools")

  for task_id, role, session in (
    ("T001", "Explorer", "explorer-backend"),
    ("T002", "Worker", "worker-backend"),
  ):
    created = call_tool(
      client,
      "create_task",
      {
        "workspace": str(workspace),
        "task": {
          "id": task_id,
          "role": role,
          "mode": "research" if role == "Explorer" else "implement",
          "title": f"{role} backend",
          "objective": "Map backend layout" if role == "Explorer" else "Add feature",
          "allowed_paths": ["backend/**"],
          "session_name": session,
        },
      },
    )
    called.add("create_task")
    if not created.get("ok"):
      errors.append(f"create_task {task_id} failed: {created}")

  listed = call_tool(client, "list_tasks", {"workspace": str(workspace)})
  called.add("list_tasks")
  if listed.get("count", 0) < 2:
    errors.append("list_tasks expected >= 2 tasks")

  got = call_tool(client, "get_task", {"workspace": str(workspace), "task_id": "T001"})
  called.add("get_task")
  if not got.get("ok") or got.get("task", {}).get("task_id") != "T001":
    errors.append(f"get_task T001 failed: {got}")
  if "task_card" not in got:
    errors.append("get_task should return task_card markdown")
  missing_task = call_tool(client, "get_task", {"workspace": str(workspace), "task_id": "ZZZ"})
  if missing_task.get("ok"):
    errors.append("get_task for unknown id should not be ok")

  updated = call_tool(
    client,
    "update_task_status",
    {"workspace": str(workspace), "task_id": "T001", "status": "running", "note": "spawned"},
  )
  called.add("update_task_status")
  if not updated.get("ok"):
    errors.append(f"update_task_status failed: {updated}")

  recorded = call_tool(
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
  called.add("record_result")
  if not recorded.get("ok"):
    errors.append(f"record_result T001 failed: {recorded}")

  allow_write = call_tool(
    client,
    "check_path_allowed",
    {"workspace": str(workspace), "task_id": "T002", "path": "backend/x.py", "operation": "write"},
  )
  called.add("check_path_allowed")
  if not allow_write.get("allowed"):
    errors.append(f"check_path_allowed should allow Worker write in scope: {allow_write}")
  secret_write = call_tool(
    client,
    "check_path_allowed",
    {"workspace": str(workspace), "task_id": "T002", "path": ".env", "operation": "write"},
  )
  if secret_write.get("allowed"):
    errors.append("check_path_allowed must block secret paths")
  outside_read = call_tool(
    client,
    "check_path_allowed",
    {"workspace": str(workspace), "task_id": "T002", "path": "frontend/y.py", "operation": "read"},
  )
  if outside_read.get("allowed"):
    errors.append("check_path_allowed must reject paths outside allowed_paths")

  call_tool(
    client,
    "record_result",
    {
      "workspace": str(workspace),
      "result": {
        "task_id": "T002",
        "session_name": "worker-backend",
        "role": "Worker",
        "status": "completed",
        "summary": "Implemented backend",
        "files_changed": ["backend/x.py"],
      },
    },
  )
  touched = call_tool(
    client,
    "record_touched_paths",
    {"workspace": str(workspace), "task_id": "T002", "files_changed": ["backend/helper.py"]},
  )
  called.add("record_touched_paths")
  if not touched.get("ok"):
    errors.append(f"record_touched_paths failed: {touched}")
  if {"backend/x.py", "backend/helper.py"} - set(touched.get("files_changed", [])):
    errors.append(f"record_touched_paths must merge files_changed: {touched}")

  skill_req = call_tool(
    client,
    "request_skill_use",
    {
      "workspace": str(workspace),
      "task_id": "T001",
      "requested_skill": "ssrd",
      "reason": "self-check skill request",
      "scope": ["backend/**"],
      "risk": "low",
    },
  )
  called.add("request_skill_use")
  request_id = skill_req.get("request_id")
  if not skill_req.get("ok") or not request_id:
    errors.append(f"request_skill_use failed: {skill_req}")

  approved = call_tool(
    client,
    "approve_skill_use",
    {"workspace": str(workspace), "request_id": request_id or "S001", "approved": True},
  )
  called.add("approve_skill_use")
  if not approved.get("ok") or not approved.get("approved"):
    errors.append(f"approve_skill_use failed: {approved}")
  denied_missing = call_tool(
    client,
    "approve_skill_use",
    {"workspace": str(workspace), "request_id": "S999", "approved": True},
  )
  if denied_missing.get("ok"):
    errors.append("approve_skill_use for unknown request should not be ok")

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
  called.add("record_finding")
  if not finding.get("ok"):
    errors.append(f"record_finding failed: {finding}")

  summary = call_tool(client, "summarize_review", {"workspace": str(workspace)})
  called.add("summarize_review")
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

  (state_dir / "changed-files.txt").write_text("backend/x.py\nbackend/helper.py\n", encoding="utf-8")

  audit = call_tool(client, "audit_scope", {"workspace": str(workspace)})
  called.add("audit_scope")
  if "ok" not in audit:
    errors.append("audit_scope missing ok field")

  report = call_tool(client, "generate_final_report", {"workspace": str(workspace)})
  called.add("generate_final_report")
  if not report.get("ok"):
    errors.append(f"generate_final_report failed: {report}")

  planned = call_tool(client, "plan_worktrees", {"workspace": str(workspace)})
  called.add("plan_worktrees")
  if not planned.get("ok"):
    errors.append(f"plan_worktrees failed: {planned}")
  if planned.get("worker_count", 0) < 1:
    errors.append(f"plan_worktrees expected >= 1 Worker (T002), got {planned.get('worker_count')}")

  readiness = call_tool(client, "check_readiness", {"client": "all"})
  called.add("check_readiness")
  if not readiness.get("ok") or "clients" not in readiness:
    errors.append(f"check_readiness failed: {readiness}")

  if called != ADVERTISED_TOOLS:
    uncalled = ADVERTISED_TOOLS - called
    unexpected = called - ADVERTISED_TOOLS
    errors.append(f"smoke coverage gap — uncalled: {sorted(uncalled)} unexpected: {sorted(unexpected)}")

  for uri in sorted(ADVERTISED_RESOURCES):
    read = client.request("resources/read", {"uri": uri})
    if not read.get("contents"):
      errors.append(f"resources/read {uri} returned no contents")

  prompt = client.request(
    "prompts/get",
    {"name": "create_worker_task_card", "arguments": {"objective": "x", "allowed_paths": "backend/**"}},
  )
  if not prompt.get("messages"):
    errors.append("prompts/get create_worker_task_card returned no messages")

  findings_doc = json.loads((state_dir / "findings" / "review-findings.json").read_text(encoding="utf-8"))
  if not any(item.get("title") == "Self-check finding" for item in findings_doc.get("findings", [])):
    errors.append("MCP finding must survive sync after generate_final_report")

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
  if not list((state_dir / "approvals").glob("S*.json")):
    errors.append("expected approval request under approvals/")

  client.close()


def check_cross_process(state_dir: Path, workspace: Path, errors: list[str]) -> None:
  """Minimal stdio transport sanity check against the same state dir."""
  client = PipeClient(state_dir)
  try:
    init = initialize(client)
    if init.get("serverInfo", {}).get("name") != "multi-agent-coordinator":
      errors.append("[cross-process] initialize missing serverInfo")
    assert_surface(client, errors, scope="cross-process")
    listed = call_tool(client, "list_tasks", {"workspace": str(workspace)})
    if listed.get("count", 0) < 2:
      errors.append("[cross-process] list_tasks should read state written in-process")
  finally:
    client.close()


def run_self_check() -> int:
  errors: list[str] = []

  if ADVERTISED_TOOLS != EXPECTED_TOOLS:
    errors.append(f"server.TOOLS {sorted(ADVERTISED_TOOLS)} != expected {sorted(EXPECTED_TOOLS)}")
  if ADVERTISED_RESOURCES != EXPECTED_RESOURCES:
    errors.append(f"server.RESOURCES {sorted(ADVERTISED_RESOURCES)} != expected {sorted(EXPECTED_RESOURCES)}")
  if ADVERTISED_PROMPTS != EXPECTED_PROMPTS:
    errors.append(f"server.PROMPTS {sorted(ADVERTISED_PROMPTS)} != expected {sorted(EXPECTED_PROMPTS)}")

  with tempfile.TemporaryDirectory(prefix="mcp-coordinator-") as tmp:
    state_dir = Path(tmp) / ".codex-multi-agent"
    state_dir.mkdir()
    workspace = Path(tmp) / "workspace"
    workspace.mkdir()

    check_in_process(state_dir, workspace, errors)
    check_cross_process(state_dir, workspace, errors)

  if errors:
    print(json.dumps({"ok": False, "errors": errors}, indent=2))
    return 1
  print(
    json.dumps(
      {
        "ok": True,
        "message": "multi-agent-coordinator MCP self-check passed",
        "tools_covered": sorted(ADVERTISED_TOOLS),
        "tool_count": len(ADVERTISED_TOOLS),
        "resource_count": len(ADVERTISED_RESOURCES),
        "prompt_count": len(ADVERTISED_PROMPTS),
      },
      indent=2,
    )
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(run_self_check())
