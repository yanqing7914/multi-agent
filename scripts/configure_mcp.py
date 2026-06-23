#!/usr/bin/env python3
"""One-step MCP registration for the multi-agent-coordinator server.

Turns the per-client config templates in `mcp/multi-agent-coordinator/clients/`
into a ready-to-use config for Cursor / Claude Code / Codex, substituting the
real repo path, workspace path, and Python interpreter.

Safety: defaults to --dry-run (prints what *would* be written, touches nothing).
Pass --write to actually merge into the target config file. JSON clients
(Cursor, Claude Code) are merged in place, preserving any existing mcpServers.
Codex uses TOML (`~/.codex/config.toml`); since stdlib cannot safely rewrite
TOML, we print the exact `[mcp_servers.*]` block to paste.

Examples:
  python scripts/configure_mcp.py --client cursor --scope project --workspace .
  python scripts/configure_mcp.py --client all --workspace . --write
  python scripts/configure_mcp.py --self-check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENTS_DIR = REPO_ROOT / "mcp" / "multi-agent-coordinator" / "clients"
SERVER_KEY = "multi-agent-coordinator"

# format: "json" merges into a JSON file; "toml" is print-only guidance.
MCP_CLIENTS = {
    "cursor": {
        "template": "cursor-mcp.json",
        "format": "json",
        "user": Path.home() / ".cursor" / "mcp.json",
        "project": Path(".cursor") / "mcp.json",
    },
    "claude": {
        "template": "claude-code-mcp.json",
        "format": "json",
        "user": Path.home() / ".claude.json",
        "project": Path(".mcp.json"),
    },
    "codex": {
        "template": "codex-mcp.json",
        "format": "toml",
        "user": Path.home() / ".codex" / "config.toml",
        "project": Path(".codex") / "config.toml",
    },
    # Hermes Agent reads ~/.hermes/config.yaml (mcp_servers key). stdlib has no
    # YAML writer, so we render a paste-ready block (print-only), like Codex TOML.
    # The codex-mcp.json structure (type/command/args/cwd) maps cleanly to stdio.
    "hermes": {
        "template": "codex-mcp.json",
        "format": "yaml",
        "user": Path.home() / ".hermes" / "config.yaml",
        "project": Path(".hermes") / "config.yaml",
    },
}


def render_template(client: str, repo_root: Path, workspace_root: Path, python_cmd: str) -> dict:
    template_path = CLIENTS_DIR / MCP_CLIENTS[client]["template"]
    raw = template_path.read_text(encoding="utf-8")
    raw = raw.replace("{REPO_ROOT}", repo_root.as_posix()).replace(
        "{WORKSPACE_ROOT}", workspace_root.as_posix()
    )
    data = json.loads(raw)
    server = data.get("mcpServers", {}).get(SERVER_KEY, {})
    if server.get("command") in {"python3", "python"}:
        server["command"] = python_cmd
    return data


def to_toml_block(server: dict) -> str:
    """Render a single mcp_servers entry as a Codex config.toml block."""
    lines = [f"[mcp_servers.{SERVER_KEY}]"]
    for key in ("command", "cwd", "type"):
        if key in server:
            lines.append(f'{key} = {json.dumps(server[key])}')
    if "args" in server:
        args = ", ".join(json.dumps(a) for a in server["args"])
        lines.append(f"args = [{args}]")
    if server.get("env"):
        lines.append(f"[mcp_servers.{SERVER_KEY}.env]")
        for env_key, env_val in server["env"].items():
            lines.append(f"{env_key} = {json.dumps(env_val)}")
    return "\n".join(lines)


def to_yaml_block(server: dict) -> str:
    """Render a single mcp_servers entry as a Hermes ~/.hermes/config.yaml block."""
    lines = ["mcp_servers:", f"  {SERVER_KEY}:"]
    for key in ("type", "command", "cwd"):
        if key in server:
            lines.append(f'    {key}: "{server[key]}"')
    if "args" in server:
        lines.append("    args:")
        lines.extend(f'      - "{a}"' for a in server["args"])
    if server.get("env"):
        lines.append("    env:")
        for env_key, env_val in server["env"].items():
            lines.append(f'      {env_key}: "{env_val}"')
    return "\n".join(lines)


def merge_json_config(existing_text: str | None, rendered: dict) -> dict:
    base: dict = {}
    if existing_text:
        try:
            loaded = json.loads(existing_text)
            if isinstance(loaded, dict):
                base = loaded
        except json.JSONDecodeError:
            base = {}
    servers = base.setdefault("mcpServers", {})
    servers[SERVER_KEY] = rendered["mcpServers"][SERVER_KEY]
    return base


def target_path(client: str, scope: str, workspace_root: Path) -> Path:
    config = MCP_CLIENTS[client]
    if scope == "user":
        return Path(config["user"])
    return (workspace_root / config["project"]).resolve()


def configure_client(
    client: str,
    scope: str,
    workspace_root: Path,
    python_cmd: str,
    write: bool,
) -> dict:
    config = MCP_CLIENTS[client]
    rendered = render_template(client, REPO_ROOT, workspace_root, python_cmd)
    server = rendered["mcpServers"][SERVER_KEY]
    dest = target_path(client, scope, workspace_root)

    result: dict = {
        "client": client,
        "format": config["format"],
        "scope": scope,
        "target": str(dest),
        "server": server,
    }

    if config["format"] in ("toml", "yaml"):
        if config["format"] == "toml":
            result["toml_block"] = to_toml_block(server)
            result["note"] = (
                "Codex uses config.toml. Paste the toml_block into the file above "
                "(under existing content); not auto-merged to avoid corrupting TOML."
            )
        else:
            result["yaml_block"] = to_yaml_block(server)
            result["note"] = (
                "Hermes uses ~/.hermes/config.yaml. Paste the yaml_block under the "
                "top-level mcp_servers key; not auto-merged to avoid corrupting YAML."
            )
        result["written"] = False
        return result

    existing = dest.read_text(encoding="utf-8") if dest.is_file() else None
    merged = merge_json_config(existing, rendered)
    result["merged"] = merged
    result["preexisting_servers"] = sorted(
        (json.loads(existing).get("mcpServers", {}) if existing else {}).keys()
    ) if existing else []

    if write:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        result["written"] = True
    else:
        result["written"] = False
        result["dry_run"] = True
    return result


def run_self_check() -> int:
    import tempfile

    errors: list[str] = []
    workspace = Path(tempfile.mkdtemp(prefix="configure-mcp-selfcheck-"))
    try:
        # 1. Every client template renders with no leftover placeholders.
        for client in MCP_CLIENTS:
            rendered = render_template(client, REPO_ROOT, workspace, "python3")
            text = json.dumps(rendered)
            if "{REPO_ROOT}" in text or "{WORKSPACE_ROOT}" in text:
                errors.append(f"{client}: unsubstituted placeholder remains")
            server = rendered["mcpServers"].get(SERVER_KEY)
            if not server or "server.py" not in " ".join(server.get("args", [])):
                errors.append(f"{client}: server entry missing server.py arg")

        # 2. Python command override applies.
        rendered = render_template("cursor", REPO_ROOT, workspace, "/custom/python")
        if rendered["mcpServers"][SERVER_KEY]["command"] != "/custom/python":
            errors.append("python command override not applied")

        # 3. JSON merge preserves a pre-existing server.
        existing = json.dumps({"mcpServers": {"other-server": {"command": "x"}}})
        merged = merge_json_config(existing, rendered)
        if "other-server" not in merged["mcpServers"]:
            errors.append("merge dropped a pre-existing server")
        if SERVER_KEY not in merged["mcpServers"]:
            errors.append("merge did not add our server")

        # 4. dry-run writes nothing; --write creates the file.
        dry = configure_client("cursor", "project", workspace, "python3", write=False)
        if dry.get("written") or (workspace / ".cursor" / "mcp.json").exists():
            errors.append("dry-run must not write a file")
        wet = configure_client("cursor", "project", workspace, "python3", write=True)
        dest = Path(wet["target"])
        if not wet.get("written") or not dest.is_file():
            errors.append("--write did not create the config file")
        else:
            reloaded = json.loads(dest.read_text(encoding="utf-8"))
            if SERVER_KEY not in reloaded.get("mcpServers", {}):
                errors.append("written config missing our server")

        # 5. Codex renders a TOML block (print-only).
        codex = configure_client("codex", "project", workspace, "python3", write=False)
        if "toml_block" not in codex or f"[mcp_servers.{SERVER_KEY}]" not in codex["toml_block"]:
            errors.append("codex toml_block not generated")

        # 6. Hermes renders a YAML block (print-only) and writes nothing.
        hermes = configure_client("hermes", "project", workspace, "python3", write=False)
        if "yaml_block" not in hermes or "mcp_servers:" not in hermes["yaml_block"]:
            errors.append("hermes yaml_block not generated")
        if SERVER_KEY not in hermes.get("yaml_block", ""):
            errors.append("hermes yaml_block missing server key")
    finally:
        import shutil

        shutil.rmtree(workspace, ignore_errors=True)

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "configure_mcp self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--client", choices=["all", *MCP_CLIENTS.keys()], default="all")
    parser.add_argument("--scope", choices=["user", "project"], default="project")
    parser.add_argument("--workspace", default=".", help="Workspace root (default: cwd)")
    parser.add_argument("--python", default=sys.executable, help="Python command/path for the server (default: this interpreter)")
    parser.add_argument("--write", action="store_true", help="Actually write/merge config (default: dry-run)")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    workspace_root = Path(args.workspace).expanduser().resolve()
    clients = list(MCP_CLIENTS) if args.client == "all" else [args.client]
    results = [
        configure_client(client, args.scope, workspace_root, args.python, args.write)
        for client in clients
    ]
    payload = {
        "ok": True,
        "mode": "write" if args.write else "dry-run",
        "repo_root": str(REPO_ROOT),
        "workspace_root": str(workspace_root),
        "results": results,
        "hint": "Re-run with --write to apply JSON merges; for Codex, paste the toml_block into config.toml.",
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
