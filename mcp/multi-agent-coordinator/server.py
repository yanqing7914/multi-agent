#!/usr/bin/env python3
"""Minimal MCP server (JSON-RPC over stdio) for multi-agent mission control."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from coordinator import (
    SERVER_VERSION,
    approve_skill_use,
    audit_scope,
    check_path_allowed,
    create_task,
    generate_final_report,
    get_task,
    list_framework_tools,
    list_tasks,
    read_resource,
    record_finding,
    record_result,
    record_touched_paths,
    request_skill_use,
    resolve_state_dir,
    resolve_workspace_root,
    summarize_review,
    update_task_status,
)

SERVER_NAME = "multi-agent-coordinator"
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "list_framework_tools",
        "description": "List dependency-free tools/ wrappers (git_tool, test_runner_tool, etc.).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "create_task",
        "description": "Create an Explorer, Worker, Reviewer, or Verifier task card.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "task": {"type": "object"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "list_tasks",
        "description": "List tasks from ownership.json with optional status/role filters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "running", "completed", "blocked", "failed", "any"]},
                "role": {"type": "string", "enum": ["Explorer", "Worker", "Reviewer", "Verifier", "any"]},
            },
        },
    },
    {
        "name": "get_task",
        "description": "Get a task by id including task card markdown when present.",
        "inputSchema": {
            "type": "object",
            "properties": {"workspace": {"type": "string"}, "task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "update_task_status",
        "description": "Update task status via update_task_status.py (syncs gates).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "task_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "running", "completed", "blocked", "failed"]},
                "note": {"type": "string"},
            },
            "required": ["task_id", "status"],
        },
    },
    {
        "name": "record_result",
        "description": "Write a result report JSON/Markdown and sync status.",
        "inputSchema": {
            "type": "object",
            "properties": {"workspace": {"type": "string"}, "result": {"type": "object"}},
            "required": ["result"],
        },
    },
    {
        "name": "check_path_allowed",
        "description": "Check whether a path is allowed for a task (read/write).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "task_id": {"type": "string"},
                "path": {"type": "string"},
                "operation": {"type": "string", "enum": ["read", "write"]},
            },
            "required": ["task_id", "path", "operation"],
        },
    },
    {
        "name": "record_touched_paths",
        "description": "Append files_changed to a task result report.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "task_id": {"type": "string"},
                "files_changed": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["task_id", "files_changed"],
        },
    },
    {
        "name": "request_skill_use",
        "description": "Request approval to use a skill for a task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "task_id": {"type": "string"},
                "requested_skill": {"type": "string"},
                "reason": {"type": "string"},
                "scope": {"type": "array", "items": {"type": "string"}},
                "risk": {"type": "string"},
            },
            "required": ["task_id", "requested_skill", "reason"],
        },
    },
    {
        "name": "approve_skill_use",
        "description": "Approve or deny a skill-use request.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "request_id": {"type": "string"},
                "approved": {"type": "boolean"},
                "approved_scope": {"type": "array", "items": {"type": "string"}},
                "expires_after_task": {"type": "boolean"},
            },
            "required": ["request_id", "approved"],
        },
    },
    {
        "name": "record_finding",
        "description": "Append a reviewer finding to findings/review-findings.json.",
        "inputSchema": {
            "type": "object",
            "properties": {"workspace": {"type": "string"}, "finding": {"type": "object"}},
            "required": ["finding"],
        },
    },
    {
        "name": "summarize_review",
        "description": "Summarize review findings by severity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "include_resolved": {"type": "boolean"},
                "group_duplicates": {"type": "boolean"},
            },
        },
    },
    {
        "name": "audit_scope",
        "description": "Run audit_worker_output.py --write-audit against current state.",
        "inputSchema": {
            "type": "object",
            "properties": {"workspace": {"type": "string"}},
        },
    },
    {
        "name": "generate_final_report",
        "description": "Generate run summary via update_task_status.py --summarize.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace": {"type": "string"},
                "include_tasks": {"type": "boolean"},
                "include_findings": {"type": "boolean"},
                "include_validation": {"type": "boolean"},
            },
        },
    },
]

RESOURCES = [
    {"uri": "multi-agent://state", "name": "state", "description": "status.json gate and task state", "mimeType": "application/json"},
    {"uri": "multi-agent://tasks", "name": "tasks", "description": "Task card directory listing", "mimeType": "application/json"},
    {"uri": "multi-agent://findings", "name": "findings", "description": "review-findings.json", "mimeType": "application/json"},
    {"uri": "multi-agent://approvals", "name": "approvals", "description": "Skill-use approval requests", "mimeType": "application/json"},
]

PROMPTS = {
    "create_worker_task_card": {
        "name": "create_worker_task_card",
        "description": "Template for creating a scoped Worker task card.",
        "arguments": [
            {"name": "objective", "description": "What the worker should implement", "required": True},
            {"name": "allowed_paths", "description": "Glob patterns the worker may edit", "required": True},
        ],
    },
    "create_review_agents_with_ssrd": {
        "name": "create_review_agents_with_ssrd",
        "description": "Template for spawning read-only Reviewer agents with ssrd skill.",
        "arguments": [
            {"name": "focus", "description": "Review focus area", "required": True},
        ],
    },
    "summarize_multi_agent_results": {
        "name": "summarize_multi_agent_results",
        "description": "Guide Main to summarize gates, findings, and next steps.",
        "arguments": [],
    },
    "audit_before_final_delivery": {
        "name": "audit_before_final_delivery",
        "description": "Guide Main through scope audit before final delivery.",
        "arguments": [],
    },
}

PROMPT_TEXT = {
    "create_worker_task_card": (
        "Create a Worker task card with:\n"
        "- role: Worker, mode: implement\n"
        "- allowed_paths: {allowed_paths}\n"
        "- forbidden_paths: secrets (.env, *.pem, credentials)\n"
        "- objective: {objective}\n"
        "- validation_required: run targeted tests\n"
        "Use create_task MCP tool. Worker must write JSON + Markdown result reports before completion."
    ),
    "create_review_agents_with_ssrd": (
        "Create a Reviewer task card with:\n"
        "- role: Reviewer, mode: review\n"
        "- allowed_paths: **/* (read-only)\n"
        "- may_use_skills: [ssrd]\n"
        "- focus: {focus}\n"
        "Request ssrd via request_skill_use if not pre-approved. Record findings with record_finding."
    ),
    "summarize_multi_agent_results": (
        "Main: run summarize_review and generate_final_report MCP tools.\n"
        "Triage findings by severity. Confirm all gates in status.json are passed.\n"
        "Use templates/final-delivery.md for user-facing delivery."
    ),
    "audit_before_final_delivery": (
        "Main: capture git diff to .codex-multi-agent/changed-files.txt,\n"
        "then run audit_scope MCP tool. Fix violations before final_delivery gate.\n"
        "Re-sync with update_task_status via --sync if using scripts directly."
    ),
}


class MCPServer:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self._initialized = False

    def workspace_root(self, args: dict) -> Path:
        return resolve_workspace_root(self.state_dir, args.get("workspace"))

    def handle(self, message: dict) -> dict | None:
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params") or {}

        if method == "notifications/initialized":
            return None

        if method == "initialize":
            self._initialized = True
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                },
            }

        if not self._initialized and method not in {"initialize"}:
            return self._error(msg_id, -32002, "Server not initialized")

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}

        if method == "tools/call":
            return self._tool_call(msg_id, params)

        if method == "resources/list":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"resources": RESOURCES}}

        if method == "resources/read":
            uri = params.get("uri", "")
            try:
                mime, text = read_resource(uri, self.state_dir)
            except FileNotFoundError as exc:
                return self._error(msg_id, -32602, str(exc))
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "contents": [{"uri": uri, "mimeType": mime, "text": text}],
                },
            }

        if method == "prompts/list":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {"prompts": list(PROMPTS.values())}}

        if method == "prompts/get":
            name = params.get("name", "")
            if name not in PROMPT_TEXT:
                return self._error(msg_id, -32602, f"Unknown prompt: {name}")
            args = {a.get("name"): (params.get("arguments") or {}).get(a.get("name"), "") for a in PROMPTS[name].get("arguments", [])}
            template = PROMPT_TEXT[name]
            try:
                text = template.format(**args)
            except KeyError:
                text = template
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "description": PROMPTS[name]["description"],
                    "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
                },
            }

        if method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        return self._error(msg_id, -32601, f"Method not found: {method}")

    def _tool_call(self, msg_id: Any, params: dict) -> dict:
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        try:
            result = self._dispatch_tool(name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                    "isError": not result.get("ok", True),
                },
            }
        except Exception as exc:  # noqa: BLE001 — surface tool errors to MCP client
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps({"ok": False, "error": str(exc)})}],
                    "isError": True,
                },
            }

    def _dispatch_tool(self, name: str, args: dict) -> dict:
        ws = self.workspace_root(args)
        sd = self.state_dir

        if name == "list_framework_tools":
            return list_framework_tools()
        if name == "create_task":
            return create_task(sd, ws, args["task"])
        if name == "list_tasks":
            return list_tasks(sd, args.get("status", "any"), args.get("role", "any"))
        if name == "get_task":
            return get_task(sd, args["task_id"])
        if name == "update_task_status":
            return update_task_status(sd, args["task_id"], args["status"], args.get("note"))
        if name == "record_result":
            return record_result(sd, args["result"])
        if name == "check_path_allowed":
            return check_path_allowed(sd, args["task_id"], args["path"], args.get("operation", "read"))
        if name == "record_touched_paths":
            return record_touched_paths(sd, args["task_id"], args.get("files_changed") or [])
        if name == "request_skill_use":
            return request_skill_use(
                sd, args["task_id"], args["requested_skill"], args["reason"],
                args.get("scope"), args.get("risk"),
            )
        if name == "approve_skill_use":
            return approve_skill_use(
                sd, args["request_id"], args["approved"],
                args.get("approved_scope"), args.get("expires_after_task", True),
            )
        if name == "record_finding":
            return record_finding(sd, args["finding"])
        if name == "summarize_review":
            return summarize_review(
                sd, args.get("include_resolved", False), args.get("group_duplicates", True),
            )
        if name == "audit_scope":
            return audit_scope(sd)
        if name == "generate_final_report":
            return generate_final_report(
                sd,
                args.get("include_tasks", True),
                args.get("include_findings", True),
                args.get("include_validation", True),
            )
        raise ValueError(f"Unknown tool: {name}")

    @staticmethod
    def _error(msg_id: Any, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def run_stdio_server(state_dir: Path) -> int:
    server = MCPServer(state_dir)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = server.handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", help="Mission control state directory (default: .codex-multi-agent)")
    args = parser.parse_args()

    env_state = os.environ.get("WORKSPACE")
    state_dir = resolve_state_dir(
        args.state_dir or (Path(env_state) / ".codex-multi-agent" if env_state else None),
    )
    state_dir.mkdir(parents=True, exist_ok=True)
    return run_stdio_server(state_dir)


if __name__ == "__main__":
    raise SystemExit(main())
