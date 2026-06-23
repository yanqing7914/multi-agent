#!/usr/bin/env python3
"""multi-agent-coding doctor: friendly readiness report with Chinese next steps.

A more user-friendly companion to `install_native_skills.py --check`. It inspects,
per client (Codex / Cursor / Claude Code):

  - whether the native skill is installed,
  - whether the bundled native agent / subagent files are installed,
  - whether the App/CLI tooling is present (CLI binary on PATH + best-effort
    config-directory detection),
  - whether complete Worker orchestration is ready,

and prints concrete "下一步怎么补齐" (how to finish setup) hints in Chinese.

Usage:
  python scripts/doctor.py                 # friendly Chinese report (default)
  python scripts/doctor.py --client cursor # one client only
  python scripts/doctor.py --json          # machine-readable JSON
  python scripts/doctor.py --self-check    # deterministic logic validation
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import install_native_skills as installer  # noqa: E402

CLIENT_ORDER = ["codex", "cursor", "claude", "hermes"]

CLIENT_LABEL = {
    "codex": "Codex",
    "cursor": "Cursor",
    "claude": "Claude Code",
    "hermes": "Hermes",
}

SKILL_NAME = {
    "codex": "codex-multi-agent",
    "cursor": "cursor-multi-agent",
    "claude": "claude-code-multi-agent",
    "hermes": "hermes-multi-agent",
}

# CLI binaries that power the scripted bridge / Worker automation per client.
# Cursor accepts either `agent` (current) or `cursor-agent` (legacy alias).
CLI_BINS = {
    "codex": ["codex"],
    "cursor": ["agent", "cursor-agent"],
    "claude": ["claude"],
    "hermes": ["hermes"],
}

CLI_LABEL = {
    "codex": "codex",
    "cursor": "agent / cursor-agent",
    "claude": "claude",
    "hermes": "hermes",
}

# Best-effort App/CLI footprint markers (relative to home). These are files the
# App or CLI creates on its own; the installer does NOT create them, so they are
# a heuristic signal that the client itself is present on this machine.
APP_MARKERS = {
    "codex": [
        ".codex/config.toml",
        ".codex/config.json",
        ".codex/auth.json",
        ".codex/sessions",
        ".codex/history.jsonl",
        ".codex/log",
    ],
    "cursor": [
        ".cursor/cli-config.json",
        ".cursor/mcp.json",
        ".cursor/argv.json",
        ".cursor/extensions",
    ],
    "claude": [
        ".claude.json",
        ".claude/settings.json",
        ".claude/projects",
        ".claude/statsig",
        ".claude/history.jsonl",
    ],
    "hermes": [
        ".hermes/config.yaml",
        ".hermes/config.yml",
        ".hermes/sessions",
        ".hermes/memory",
        ".hermes",
    ],
}

# Common off-PATH install locations to probe so we can say "installed but not on
# PATH" instead of just "missing".
OFFPATH_DIRS = [
    Path.home() / ".local" / "bin",
    Path.home() / "bin",
]
WIN_BIN_SUFFIXES = [".exe", ".cmd", ".bat", ""]


def _which_any(names: list[str]) -> dict[str, bool]:
    return {name: bool(shutil.which(name)) for name in names}


def _probe_offpath(names: list[str]) -> list[str]:
    """Return file paths for binaries found in common dirs but not on PATH."""
    found: list[str] = []
    suffixes = WIN_BIN_SUFFIXES if sys.platform.startswith("win") else [""]
    for name in names:
        if shutil.which(name):
            continue
        for directory in OFFPATH_DIRS:
            for suffix in suffixes:
                candidate = directory / f"{name}{suffix}"
                if candidate.is_file():
                    found.append(str(candidate))
                    break
    return found


def probe_client(client: str) -> dict:
    """Inspect machine state for one client (touches filesystem + PATH)."""
    config = installer.CLIENTS[client]

    skill_paths = [str(p) for p in config["destinations"] if (p / "SKILL.md").is_file()]

    agent_dest = config.get("agent_dest")
    expects_native_agents = agent_dest is not None
    expected_agent_names = installer.bundled_agent_names(client) if expects_native_agents else []
    agent_paths = (
        [str(agent_dest / name) for name in expected_agent_names if (agent_dest / name).is_file()]
        if expects_native_agents
        else []
    )
    agents_installed = bool(agent_paths) if expects_native_agents else True

    cli_bins = _which_any(CLI_BINS[client])
    cli_present = any(cli_bins.values())
    cli_offpath = _probe_offpath(CLI_BINS[client])

    markers_present = [m for m in APP_MARKERS[client] if (Path.home() / m).exists()]

    extra: dict = {}
    if client == "cursor":
        extra = {
            "bash": bool(shutil.which("bash")),
            "tmux": bool(shutil.which("tmux")),
        }

    return {
        "client": client,
        "label": CLIENT_LABEL[client],
        "skill_name": SKILL_NAME[client],
        "skill_installed": bool(skill_paths),
        "skill_paths": skill_paths,
        "expects_native_agents": expects_native_agents,
        "expected_agent_names": expected_agent_names,
        "agents_installed": agents_installed,
        "agent_paths": agent_paths,
        "agent_dest": str(agent_dest) if agent_dest else None,
        "cli_label": CLI_LABEL[client],
        "cli_bins": cli_bins,
        "cli_present": cli_present,
        "cli_offpath": cli_offpath,
        "bridge_ready": installer.worker_bridge_ready(client, cli_bins),
        "config_detected": bool(markers_present),
        "config_markers": markers_present,
        "extra": extra,
    }


def verdict(status: dict) -> dict:
    """Pure verdict from a status dict (no I/O); used by report + self-check."""
    if not status["skill_installed"]:
        return {"ready": False, "level": "missing", "headline": "未安装原生 skill"}
    if status["expects_native_agents"] and not status["agents_installed"]:
        return {"ready": False, "level": "partial", "headline": "skill 已安装，但缺少原生 subagent 文件"}
    if status["client"] == "cursor" and not status["cli_present"]:
        return {"ready": False, "level": "partial", "headline": "skill 已安装，但自动 Worker 需要本机 Cursor CLI"}
    return {"ready": True, "level": "ready", "headline": "就绪"}


def remediation(status: dict) -> list[str]:
    """Pure list of Chinese next-step hints from a status dict (no I/O)."""
    client = status["client"]
    steps: list[str] = []

    if not status["skill_installed"]:
        steps.append(
            f"安装原生 skill：python scripts/install_native_skills.py --client {client} --scope primary --force"
            f"（或解压对应 release zip 后在包根目录运行），随后重启 / 重新加载 {status['label']}。"
        )

    if status["expects_native_agents"] and not status["agents_installed"]:
        joined = "、".join(status["expected_agent_names"]) or "原生 subagent 文件"
        steps.append(
            f"缺少原生 subagent：重新运行安装并加 --force，会写入 {status['agent_dest']} 下的 {joined}。"
        )

    if client == "codex":
        if not status["cli_present"]:
            steps.append(
                "（可选）安装 codex CLI 才能用脚本 bridge `--runtime codex`；Codex App 用原生 subagent 不依赖它。"
            )
        if verdict(status)["ready"]:
            steps.append('就绪：在 Codex 里说"用 codex-multi-agent 开 Worker + Reviewer 改一个小 demo"即可触发原生 subagent。')

    elif client == "cursor":
        if not status["cli_present"]:
            steps.append(
                "安装 Cursor CLI（自动 Worker 编排所需，App 加载 skill 本身并不需要它）："
            )
            steps.append("    Windows PowerShell：irm 'https://cursor.com/install?win32=true' | iex")
            steps.append("    macOS / Linux / WSL：curl https://cursor.com/install -fsS | bash")
            steps.append("    安装后重开终端，运行 `agent --version` 验证；若提示找不到命令，把 ~/.local/bin 加入 PATH。")
        if status["cli_offpath"]:
            steps.append(
                "检测到 Cursor CLI 但不在 PATH 上：" + "、".join(status["cli_offpath"]) + "；把其所在目录加入 PATH 后重开终端。"
            )
        extra = status.get("extra", {})
        if not extra.get("bash", True) or not extra.get("tmux", True):
            missing = [name for name in ("bash", "tmux") if not extra.get(name, True)]
            steps.append(
                "自动 Worker bridge 还需要 " + " + ".join(missing) + "（Windows 原生不带 tmux，建议在 WSL 里运行 bridge）。"
            )
        steps.append("没有 CLI 也能用手动降级：python scripts/run_multi_agent.py --runtime cursor-desktop --task-card ...，再把生成的 prompt 贴进 Cursor Agent。")
        if verdict(status)["ready"]:
            steps.append('就绪：在 Cursor 里说"用 cursor-multi-agent 拆成任务卡，并通过本机 agent CLI 跑 Worker，回收报告后做 diff 审计"。')

    elif client == "claude":
        if not status["cli_present"]:
            steps.append(
                "（可选）安装 standalone claude CLI 才能用脚本 bridge `--runtime claude-code`；Claude Code App/IDE 用内置 subagents 不依赖它。"
            )
        if verdict(status)["ready"]:
            steps.append('就绪：在 Claude Code 里说"用 claude-code-multi-agent 开 Worker + Reviewer + Verifier"，会调用 .claude/agents 下的 subagents。')

    elif client == "hermes":
        if not status["cli_present"]:
            steps.append(
                "（可选）安装 Hermes Agent 才能在本机跑 always-on persistent agent；App 加载可移植 SKILL.md 本身不依赖它。"
            )
        steps.append(
            "把 MCP coordinator 注册进 Hermes：python scripts/configure_mcp.py --client hermes（生成 ~/.hermes/config.yaml 的 mcp_servers 片段，粘贴即可）。"
        )
        if verdict(status)["ready"]:
            steps.append('就绪：在 Hermes 里用 hermes-multi-agent，通过原生 MCP 工具 + mission-control 脚本拆任务卡、回收报告、做 scope 审计。')

    if not steps:
        steps.append("一切就绪，无需额外操作。")
    return steps


def build_report(clients: list[str]) -> dict:
    entries = []
    for client in clients:
        status = probe_client(client)
        status["verdict"] = verdict(status)
        status["next_steps"] = remediation(status)
        entries.append(status)
    return {
        "ok": True,
        "home": str(Path.home()),
        "platform": sys.platform,
        "clients": entries,
        "all_ready": all(e["verdict"]["ready"] for e in entries),
    }


def _mark(value: bool) -> str:
    return "✓" if value else "✗"


def render_human(report: dict) -> str:
    lines: list[str] = []
    bar = "=" * 60
    lines.append(bar)
    lines.append(" multi-agent-coding 体检报告 (doctor)")
    lines.append(f" home     : {report['home']}")
    lines.append(f" platform : {report['platform']}")
    lines.append(bar)

    for entry in report["clients"]:
        v = entry["verdict"]
        lines.append("")
        lines.append(f"[{entry['label']}]  {entry['skill_name']}  ->  {_mark(v['ready'])} {v['headline']}")

        skill_loc = entry["skill_paths"][0] if entry["skill_paths"] else "未发现"
        lines.append(f"  原生 skill 已安装   : {_mark(entry['skill_installed'])}  {skill_loc}")

        if entry["expects_native_agents"]:
            names = "、".join(Path(p).name for p in entry["agent_paths"]) or "未发现"
            lines.append(f"  原生 subagent 文件  : {_mark(entry['agents_installed'])}  {names}")

        cli_note = "App 不依赖，脚本 bridge 需要" if entry["client"] != "cursor" else "自动 Worker 编排所需"
        lines.append(f"  CLI ({entry['cli_label']}) : {_mark(entry['cli_present'])}  ({cli_note})")

        if entry["client"] == "cursor":
            extra = entry.get("extra", {})
            lines.append(
                f"  bridge 依赖 bash/tmux : bash={_mark(extra.get('bash', False))} tmux={_mark(extra.get('tmux', False))}"
            )

        lines.append(f"  App/CLI 配置痕迹    : {_mark(entry['config_detected'])}  (启发式检测)")
        lines.append(f"  完整 Worker 编排    : {_mark(v['ready'])}  {v['headline']}")

        lines.append("  下一步:")
        for step in entry["next_steps"]:
            lines.append(f"    - {step}")

    lines.append("")
    lines.append("-" * 60)
    summary = " | ".join(
        f"{e['label']} {_mark(e['verdict']['ready'])}" for e in report["clients"]
    )
    overall = "全部就绪" if report["all_ready"] else "存在待补齐项，见上方下一步"
    lines.append(f" 汇总: {summary}    总体: {overall}")
    lines.append("-" * 60)
    return "\n".join(lines)


def _force_utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except Exception:
            pass


def self_check() -> int:
    """Deterministic validation of doctor's pure logic (no machine dependence)."""
    errors: list[str] = []

    # 1. probe_client returns a well-formed schema for every client.
    required_keys = {
        "client", "label", "skill_name", "skill_installed", "skill_paths",
        "expects_native_agents", "agents_installed", "cli_present", "cli_bins",
        "bridge_ready", "config_detected",
    }
    for client in CLIENT_ORDER:
        status = probe_client(client)
        missing = required_keys - set(status)
        if missing:
            errors.append(f"{client}: probe missing keys {sorted(missing)}")
        if not isinstance(remediation({**status, "verdict": verdict(status)}), list):
            errors.append(f"{client}: remediation did not return a list")

    # 2. Synthetic "all missing" -> not ready, has install hint.
    base = {
        "client": "cursor",
        "label": "Cursor",
        "skill_name": "cursor-multi-agent",
        "skill_installed": False,
        "skill_paths": [],
        "expects_native_agents": False,
        "expected_agent_names": [],
        "agents_installed": True,
        "agent_paths": [],
        "agent_dest": None,
        "cli_present": False,
        "cli_bins": {"agent": False, "cursor-agent": False},
        "cli_offpath": [],
        "bridge_ready": False,
        "config_detected": False,
        "config_markers": [],
        "extra": {"bash": False, "tmux": False},
    }
    v_missing = verdict(base)
    if v_missing["ready"] or v_missing["level"] != "missing":
        errors.append(f"missing-skill verdict wrong: {v_missing}")
    if not any("install_native_skills" in s for s in remediation(base)):
        errors.append("missing-skill remediation lacks install hint")

    # 3. Cursor with skill but no CLI -> partial, hint mentions Cursor install URL.
    cursor_no_cli = {**base, "skill_installed": True, "skill_paths": ["/x/SKILL.md"]}
    v_partial = verdict(cursor_no_cli)
    if v_partial["ready"] or v_partial["level"] != "partial":
        errors.append(f"cursor-no-cli verdict wrong: {v_partial}")
    if not any("cursor.com/install" in s for s in remediation(cursor_no_cli)):
        errors.append("cursor-no-cli remediation lacks Cursor CLI install URL")

    # 4. Cursor with CLI present -> ready (any-of agent/cursor-agent).
    cursor_ready = {
        **cursor_no_cli,
        "cli_present": True,
        "cli_bins": {"agent": False, "cursor-agent": True},
        "bridge_ready": True,
        "extra": {"bash": True, "tmux": True},
    }
    if not verdict(cursor_ready)["ready"]:
        errors.append("cursor-with-cursor-agent should be ready")

    # 5. Codex skill but missing subagents -> partial.
    codex_partial = {
        **base,
        "client": "codex",
        "label": "Codex",
        "skill_name": "codex-multi-agent",
        "skill_installed": True,
        "skill_paths": ["/x/SKILL.md"],
        "expects_native_agents": True,
        "expected_agent_names": ["multi-agent-worker.toml"],
        "agents_installed": False,
        "agent_dest": "/home/.codex/agents",
        "cli_bins": {"codex": True},
        "cli_present": True,
        "bridge_ready": True,
        "extra": {},
    }
    if verdict(codex_partial)["level"] != "partial":
        errors.append("codex missing-subagents should be partial")

    # 6. Codex fully installed -> ready even without CLI (native subagents).
    codex_ready = {**codex_partial, "agents_installed": True, "agent_paths": ["/x.toml"], "cli_present": False, "cli_bins": {"codex": False}}
    if not verdict(codex_ready)["ready"]:
        errors.append("codex with subagents should be ready without CLI")

    # 7. Human renderer produces non-empty text for a real report.
    report = build_report(CLIENT_ORDER)
    rendered = render_human(report)
    if not rendered or "doctor" not in rendered:
        errors.append("render_human produced empty/invalid output")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=True, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "doctor self-check passed", "clients": CLIENT_ORDER}, ensure_ascii=True, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="multi-agent-coding doctor: readiness report with Chinese next steps.")
    parser.add_argument("--client", choices=["all", *CLIENT_ORDER], default="all")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of the friendly report")
    parser.add_argument("--self-check", action="store_true", help="Run deterministic logic validation (ASCII output)")
    args = parser.parse_args()

    if args.self_check:
        return self_check()

    clients = CLIENT_ORDER if args.client == "all" else [args.client]
    report = build_report(clients)

    if args.json:
        _force_utf8_stdout()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    _force_utf8_stdout()
    print(render_human(report))
    # doctor is a diagnostic; it exits 0 even when items need finishing so it is
    # safe to run in setup scripts. Use --self-check for a pass/fail gate.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
