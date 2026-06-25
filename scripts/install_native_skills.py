#!/usr/bin/env python3
"""Install multi-agent skills into native Codex/Cursor/Claude skill locations."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

CLIENTS = {
    "codex": {
        "source": REPO_ROOT / "adapters" / "codex",
        "adapter_name": "codex",
        "destinations": [
            Path.home() / ".agents" / "skills" / "codex-multi-agent",
            Path.home() / ".codex" / "skills" / "codex-multi-agent",
        ],
        "primary": Path.home() / ".agents" / "skills" / "codex-multi-agent",
        "bridge_bins": ["codex"],
        "agent_source": REPO_ROOT / "adapters" / "codex" / "agents",
        "agent_dest": Path.home() / ".codex" / "agents",
    },
    "cursor": {
        "source": REPO_ROOT / "adapters" / "cursor",
        "adapter_name": "cursor",
        "destinations": [
            Path.home() / ".agents" / "skills" / "cursor-multi-agent",
            Path.home() / ".cursor" / "skills" / "cursor-multi-agent",
        ],
        "primary": Path.home() / ".agents" / "skills" / "cursor-multi-agent",
        "bridge_bins": ["agent", "cursor-agent"],
    },
    "claude": {
        "source": REPO_ROOT / "adapters" / "claude-code",
        "adapter_name": "claude-code",
        "destinations": [
            Path.home() / ".agents" / "skills" / "claude-code-multi-agent",
            Path.home() / ".claude" / "skills" / "claude-code-multi-agent",
        ],
        "primary": Path.home() / ".claude" / "skills" / "claude-code-multi-agent",
        "bridge_bins": ["claude"],
        "agent_source": REPO_ROOT / "adapters" / "claude-code" / "agents",
        "agent_dest": Path.home() / ".claude" / "agents",
    },
    "hermes": {
        "source": REPO_ROOT / "adapters" / "hermes",
        "adapter_name": "hermes",
        "destinations": [
            Path.home() / ".agents" / "skills" / "hermes-multi-agent",
            Path.home() / ".hermes" / "skills" / "hermes-multi-agent",
        ],
        "primary": Path.home() / ".agents" / "skills" / "hermes-multi-agent",
        "bridge_bins": [],
    },
}

SHARED_ITEMS = [
    "adapters/_shared",
    "adapters/openclaw/scripts",
    "adapters/openclaw/templates",
    "checklists",
    "templates",
    "scripts/install_native_skills.py",
    "scripts/run_multi_agent.py",
    "scripts/doctor.py",
]


def source_available(client: str) -> bool:
    return (CLIENTS[client]["source"] / "SKILL.md").is_file()


def available_clients() -> list[str]:
    return [client for client in CLIENTS if source_available(client)]


def rel_to_repo(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def copy_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"), dirs_exist_ok=True)
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def destination_paths(client: str, scope: str) -> list[Path]:
    config = CLIENTS[client]
    if scope == "primary":
        return [config["primary"]]
    if scope == "all-compatible":
        return config["destinations"]
    return [Path(scope).expanduser().resolve()]


def worker_bridge_ready(client: str, bridge: dict[str, bool]) -> bool:
    """Whether Worker orchestration is available for this client once installed.

    Codex/Claude ship native subagents; Cursor's Main dispatches Workers by
    spawning Cursor subagents (in-App delegation) which needs no external CLI;
    Hermes drives via its native MCP client. For all of these, having the native
    skill installed is the App path. The Cursor `agent` CLI only powers the
    optional scripted/CI bridge, so it is not required for readiness.
    """
    if client in {"codex", "claude", "hermes", "cursor"}:
        return True
    return all(bridge.values())


def readiness_note(client: str, bridge: dict[str, bool]) -> str:
    if client == "codex":
        return (
            "Codex App and CLI can load the native skill. Full App mode uses Codex native subagents; "
            "`codex` CLI is only needed for scripted bridge/runtime `--runtime codex`."
        )
    if client == "claude":
        return (
            "Claude Code App/IDE and CLI can load the native skill. Full App/CLI mode uses bundled "
            "Claude subagents; `claude` CLI is needed for scripted bridge/runtime `--runtime claude-code`."
        )
    if client == "hermes":
        return (
            "Hermes Agent can load the portable native skill (agentskills.io standard). Worker orchestration "
            "runs through Hermes's native MCP client plus the bundled OpenClaw mission-control scripts; register "
            "the MCP coordinator with `scripts/configure_mcp.py --client hermes` (adds it to ~/.hermes/config.yaml)."
        )
    # Cursor: native skill installed = App path ready. Main dispatches Workers by
    # spawning Cursor subagents directly (in-App delegation, no external CLI). The
    # `agent` CLI is OPTIONAL and only powers the scripted/CI bridge.
    has_cli = any(bridge.values())
    cli_state = "present" if has_cli else "not installed (optional)"
    return (
        "Cursor App and CLI can load the native skill. Primary path: the Main agent dispatches Workers by "
        "spawning Cursor subagents directly (in-App delegation) — no external CLI needed. The `agent` CLI "
        f"(`agent`/`cursor-agent`) is OPTIONAL and only powers the scripted/CI bridge `run_multi_agent.py "
        f"--runtime cursor` (needs `agent` + tmux; use WSL on native Windows). CLI: {cli_state}. "
        "Install it only if you want the scripted bridge: `irm 'https://cursor.com/install?win32=true' | iex` "
        "(Windows) or `curl https://cursor.com/install -fsS | bash`."
    )


def bundled_agent_names(client: str) -> list[str]:
    config = CLIENTS[client]
    source = config.get("agent_source")
    if source and source.exists():
        return sorted(path.name for path in source.glob("*") if path.is_file())
    if client == "codex":
        return ["multi-agent-reviewer.toml", "multi-agent-worker.toml"]
    if client == "claude":
        return ["multi-agent-reviewer.md", "multi-agent-verifier.md", "multi-agent-worker.md"]
    return []


def install_client(client: str, scope: str, force: bool, agent_dest_override: Path | None = None) -> dict:
    config = CLIENTS[client]
    if not source_available(client):
        return {
            "client": client,
            "installed": [],
            "installed_agents": [],
            "native_skill_ready": False,
            "complete_worker_bridge_ready": False,
            "bridge_bins": {binary: bool(shutil.which(binary)) for binary in config["bridge_bins"]},
            "note": f"{client}: adapter source is not present in this package; use that client's release zip or the full repository.",
        }

    installed = []
    for dest in destination_paths(client, scope):
        if dest.exists() and force:
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        copy_path(config["source"] / "SKILL.md", dest / "SKILL.md")
        copy_path(config["source"] / "README.md", dest / "README.md")
        copy_path(config["source"] / "QUICKSTART.md", dest / "QUICKSTART.md")
        copy_path(config["source"], dest / "adapters" / config["adapter_name"])
        for item in SHARED_ITEMS:
            copy_path(REPO_ROOT / item, dest / item)
        installed.append(str(dest))

    installed_agents = []
    if config.get("agent_source") and config.get("agent_dest"):
        agent_dest = agent_dest_override or config["agent_dest"]
        agent_dest.mkdir(parents=True, exist_ok=True)
        for agent_file in sorted(config["agent_source"].glob("*")):
            if agent_file.is_file():
                copy_path(agent_file, agent_dest / agent_file.name)
                installed_agents.append(str(agent_dest / agent_file.name))

    bridge = {binary: bool(shutil.which(binary)) for binary in config["bridge_bins"]}
    return {
        "client": client,
        "installed": installed,
        "installed_agents": installed_agents,
        "native_skill_ready": True,
        "complete_worker_bridge_ready": worker_bridge_ready(client, bridge),
        "bridge_bins": bridge,
        "note": readiness_note(client, bridge),
    }


def check_client(client: str) -> dict:
    config = CLIENTS[client]
    discovered = [str(path) for path in config["destinations"] if (path / "SKILL.md").is_file()]
    discovered_agents = []
    if config.get("agent_dest"):
        discovered_agents = [
            str(config["agent_dest"] / name)
            for name in bundled_agent_names(client)
            if (config["agent_dest"] / name).is_file()
        ]
    bridge = {binary: bool(shutil.which(binary)) for binary in config["bridge_bins"]}
    return {
        "client": client,
        "package_source_available": source_available(client),
        "native_skill_paths": discovered,
        "native_agent_paths": discovered_agents,
        "native_skill_ready": bool(discovered),
        "complete_worker_bridge_ready": worker_bridge_ready(client, bridge),
        "bridge_bins": bridge,
        "note": readiness_note(client, bridge),
    }


def self_check() -> int:
    errors = []
    clients = available_clients()
    if not clients:
        errors.append("no client adapter sources are present in this package")
    with tempfile.TemporaryDirectory(prefix="multi-agent-native-install-") as tmp:
        tmp_root = Path(tmp)
        for client in clients:
            dest = tmp_root / client / "skill"
            agent_dest = tmp_root / client / "native-agents"
            payload = install_client(client, str(dest), force=True, agent_dest_override=agent_dest)
            if not (dest / "SKILL.md").is_file():
                errors.append(f"{client}: SKILL.md missing after install")
            for item in SHARED_ITEMS:
                expected = dest / item
                if not expected.exists():
                    errors.append(f"{client}: shared item missing {rel_to_repo(Path(item))}")
            if client == "codex" and not payload["installed_agents"]:
                errors.append("codex: custom agent files not installed")
            if client == "claude" and not payload["installed_agents"]:
                errors.append("claude: subagent files not installed")
            if client == "cursor" and payload["installed_agents"]:
                errors.append("cursor: should not install fake native subagent files")
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "native skill installer self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=["all", *CLIENTS.keys()], default="all")
    parser.add_argument("--scope", default="primary", help="primary, all-compatible, or explicit destination directory")
    parser.add_argument("--force", action="store_true", help="Replace existing destination folders")
    parser.add_argument("--check", action="store_true", help="Only report installed skill and bridge readiness")
    parser.add_argument("--self-check", action="store_true", help="Run deterministic installer validation")
    args = parser.parse_args()

    if args.self_check:
        return self_check()

    clients = available_clients() if args.client == "all" else [args.client]
    if not clients:
        print(
            json.dumps(
                {
                    "ok": False,
                    "repo_root": str(REPO_ROOT),
                    "error": "No client adapter sources are present in this package.",
                },
                indent=2,
            )
        )
        return 1
    if args.client != "all" and not source_available(args.client) and not args.check:
        print(
            json.dumps(
                {
                    "ok": False,
                    "repo_root": str(REPO_ROOT),
                    "error": f"{args.client}: adapter source is not present in this package.",
                },
                indent=2,
            )
        )
        return 1

    payload = {
        "ok": True,
        "repo_root": str(REPO_ROOT),
        "mode": "check" if args.check else "install",
        "results": [check_client(client) if args.check else install_client(client, args.scope, args.force) for client in clients],
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
