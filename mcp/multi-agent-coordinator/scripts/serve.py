#!/usr/bin/env python3
"""Friendly launcher for the multi-agent-coordinator MCP server (stdio).

Thin wrapper around ``server.run_stdio_server`` so operators do not have to
remember the server path or state-dir defaults. Behaviour matches running
``python server.py --state-dir ...`` directly; this just adds a banner (on
stderr, never stdout) and a non-blocking ``--self-check``.

Examples:
  python serve.py                         # state dir: ./.codex-multi-agent
  python serve.py --state-dir /repo/.codex-multi-agent
  WORKSPACE=/repo python serve.py         # state dir: /repo/.codex-multi-agent
  python serve.py --self-check            # verify import + construct, then exit

``--self-check`` must NEVER enter the stdin read loop: it only proves the
server module imports, constructs an ``MCPServer``, and answers a couple of
non-stdin ``handle`` calls before exiting.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

COORD_DIR = Path(__file__).resolve().parent.parent
SERVER = COORD_DIR / "server.py"

if str(COORD_DIR) not in sys.path:
  sys.path.insert(0, str(COORD_DIR))

import server as server_mod  # noqa: E402  reuse the real stdio entry point


def resolve_state_dir(raw: str | None) -> Path:
  """Mirror server.main: explicit --state-dir, else $WORKSPACE, else cwd."""
  env_state = os.environ.get("WORKSPACE")
  candidate = raw or (str(Path(env_state) / ".codex-multi-agent") if env_state else None)
  return server_mod.resolve_state_dir(candidate)


def run_self_check() -> int:
  """Prove the server is importable and constructible without reading stdin."""
  errors: list[str] = []

  for attr in ("MCPServer", "run_stdio_server", "TOOLS", "RESOURCES", "PROMPTS", "PROTOCOL_VERSION"):
    if not hasattr(server_mod, attr):
      errors.append(f"server module missing attribute: {attr}")

  if not SERVER.is_file():
    errors.append(f"server.py not found at {SERVER}")

  if not errors:
    try:
      with tempfile.TemporaryDirectory(prefix="serve-selfcheck-") as tmp:
        state_dir = Path(tmp) / ".codex-multi-agent"
        state_dir.mkdir()
        srv = server_mod.MCPServer(state_dir)
        init = srv.handle(
          {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
              "protocolVersion": server_mod.PROTOCOL_VERSION,
              "capabilities": {},
              "clientInfo": {"name": "serve-self-check", "version": "1.0"},
            },
          }
        )
        server_info = (init or {}).get("result", {}).get("serverInfo", {})
        if server_info.get("name") != "multi-agent-coordinator":
          errors.append("initialize did not return expected serverInfo")
        tools = srv.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        listed = {tool["name"] for tool in (tools or {}).get("result", {}).get("tools", [])}
        if listed != {tool["name"] for tool in server_mod.TOOLS}:
          errors.append("tools/list does not match server.TOOLS")
    except Exception as exc:  # noqa: BLE001 — surface construction failure as an error
      errors.append(f"could not construct MCPServer: {exc}")

  if errors:
    print(json.dumps({"ok": False, "errors": errors}, indent=2))
    return 1
  print(
    json.dumps(
      {
        "ok": True,
        "message": "serve.py self-check passed (import + construct, no stdin loop)",
        "server": str(SERVER),
        "tool_count": len(server_mod.TOOLS),
      },
      indent=2,
    )
  )
  return 0


def main() -> int:
  parser = argparse.ArgumentParser(
    description=__doc__,
    formatter_class=argparse.RawDescriptionHelpFormatter,
  )
  parser.add_argument(
    "--state-dir",
    help="Mission control state directory (default: ./.codex-multi-agent, or $WORKSPACE/.codex-multi-agent)",
  )
  parser.add_argument(
    "--self-check",
    action="store_true",
    help="Verify the server imports and constructs, then exit (never reads stdin)",
  )
  args = parser.parse_args()

  if args.self_check:
    return run_self_check()

  state_dir = resolve_state_dir(args.state_dir)
  state_dir.mkdir(parents=True, exist_ok=True)
  # Banner goes to stderr so stdout stays a clean JSON-RPC channel.
  print(
    f"multi-agent-coordinator MCP server (stdio) — state dir: {state_dir}",
    file=sys.stderr,
    flush=True,
  )
  return server_mod.run_stdio_server(state_dir)


if __name__ == "__main__":
  raise SystemExit(main())
