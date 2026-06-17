# Agent Install Guide

This page is written for AI agents. If a user gives you this GitHub repository and says "install this skill", install the native package for the current client instead of copying random prompts.

Repository: `https://github.com/yanqing7914/multi-agent`
Release base: `https://github.com/yanqing7914/multi-agent/releases/latest`

## Choose Package

| Client | Download | Install action | Full Worker mode |
| --- | --- | --- | --- |
| Codex App / CLI | `codex-multi-agent-skill-v0.2.0.zip` | Extract, then run `scripts/install_native_skills.py --client codex --scope primary --force` | Native Codex skills + bundled custom agents; `codex` CLI bridge is optional |
| Cursor App / CLI | `cursor-multi-agent-pack-v0.2.0.zip` | Extract, then run `scripts/install_native_skills.py --client cursor --scope primary --force` | Native Cursor skills + local `agent` CLI bridge for automatic Workers |
| Claude Code App / IDE / CLI | `claude-code-multi-agent-pack-v0.2.0.zip` | Extract, then run `scripts/install_native_skills.py --client claude --scope primary --force` | Native Claude skills + bundled `.claude/agents`; `claude` CLI bridge is optional for script launch |
| OpenClaw / Her | `openclaw-multi-agent-skill-v0.2.0.zip` | Extract `openclaw-multi-agent/` into the OpenClaw skills directory | Native OpenClaw `sessions_spawn` / `sessions_send` workflow |
| Generic agent | `multi-agent-coding-skill-v0.2.0.zip` | Extract and read `SKILL.md` | Protocol guidance only; use a client pack for native install |

## Required Behavior For Installing Agents

When acting as the user's agent:

1. Detect your client: Codex, Cursor, Claude Code, OpenClaw/Her, or other.
2. Download the matching latest release asset.
3. Extract the package into a stable temp or tool directory.
4. Run the native installer when the package includes `scripts/install_native_skills.py`.
5. Run `--check` and report whether native skill discovery and Worker automation are ready.
6. Do not claim complete Worker automation if the required bridge binary is missing.

## Native Install Commands

From an extracted client package root:

```bash
python3 scripts/install_native_skills.py --client all --scope primary --force
python3 scripts/install_native_skills.py --client all --check
```

`--client all` means "all client adapters present in this package". In a single-client package it installs only that client. In the full repository it installs Codex, Cursor, and Claude.

`--scope primary` installs to the recommended native skill directory. `--scope all-compatible` also writes compatible directories such as `.agents/skills`, `.cursor/skills`, `.claude/skills`, and `.codex/skills`.

## Codex Install

Install package: `codex-multi-agent-skill-v0.2.0.zip`.

Native locations used by the installer:

```text
~/.agents/skills/codex-multi-agent
~/.codex/skills/codex-multi-agent
~/.codex/agents/multi-agent-worker.toml
~/.codex/agents/multi-agent-reviewer.toml
```

Codex App and Codex CLI can both discover the skill after restart/reload. Full App mode uses Codex native subagents. Scripted bridge mode uses:

```bash
python3 scripts/run_multi_agent.py --runtime codex --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

If `codex` CLI is missing, native App subagents can still be full mode; only the scripted bridge is unavailable.

## Cursor Install

Install package: `cursor-multi-agent-pack-v0.2.0.zip`.

Native locations used by the installer:

```text
~/.agents/skills/cursor-multi-agent
~/.cursor/skills/cursor-multi-agent
```

Cursor App and Cursor CLI can both discover the skill. Complete automatic Worker orchestration from Cursor App requires the local Cursor CLI binary `agent` because Cursor App does not expose a public Codex/Claude-style native subagent API.

Full Worker bridge:

```bash
python3 scripts/run_multi_agent.py --runtime cursor --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

If `agent` is missing, report: native skill installed, full Worker automation blocked; manual prompt handoff remains available with `--runtime cursor-desktop`.

## Claude Code Install

Install package: `claude-code-multi-agent-pack-v0.2.0.zip`.

Native locations used by the installer:

```text
~/.claude/skills/claude-code-multi-agent
~/.agents/skills/claude-code-multi-agent
~/.claude/agents/multi-agent-worker.md
~/.claude/agents/multi-agent-reviewer.md
~/.claude/agents/multi-agent-verifier.md
```

Claude Code App/IDE and CLI can both discover the skill. Full App/CLI mode uses Claude subagents with the bundled agent files. Scripted bridge mode uses:

```bash
python3 scripts/run_multi_agent.py --runtime claude-code --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

If standalone `claude` CLI is missing, Claude Code App/IDE subagents can still use the native skill in the app surface; only terminal-launched bridge mode is unavailable.

## Smoke Test

From an extracted client package root:

```bash
python3 scripts/install_native_skills.py --self-check
python3 scripts/run_multi_agent.py --help
```

Then run the client-specific check that exists in the package:

```bash
python3 adapters/codex/scripts/codex_self_check.py
python3 adapters/cursor/scripts/cursor_self_check.py
python3 adapters/claude-code/scripts/claude_code_self_check.py
```

Only run checks whose adapter directory is present.
