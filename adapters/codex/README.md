# Codex Multi-Agent Adapter

Thin Codex layer over [`adapters/openclaw/`](../openclaw/) mission-control scripts.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## What This Enables

Codex App and Codex CLI both get:

1. A native `codex-multi-agent` skill.
2. Bundled Codex custom agents for scoped Worker and read-only Reviewer roles.
3. Native subagent orchestration when the user asks for multiple agents.
4. Optional `codex exec` bridge for deterministic script-launched workers.
5. Shared task cards, result reports, gate sync, and scope audit.

Manual prompt handoff remains available, but v0.2.0 treats native Codex subagents as the full App/CLI path.

## Install

From the extracted `codex-multi-agent-skill-v0.2.0.zip` root:

```bash
python3 scripts/install_native_skills.py --client codex --scope primary --force
python3 scripts/install_native_skills.py --client codex --check
```

The installer writes:

```text
~/.agents/skills/codex-multi-agent
~/.codex/skills/codex-multi-agent
~/.codex/agents/multi-agent-worker.toml
~/.codex/agents/multi-agent-reviewer.toml
```

## Usage: Codex App Native Subagents

Ask Codex App:

```text
Use codex-multi-agent. Split this task into scoped task cards, spawn a Worker for implementation and a Reviewer using ssrd if available, wait for result reports, run gate sync and scope audit, then deliver only after gates pass.
```

Main prepares each task-card prompt:

```bash
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex-native \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Then Main spawns a native Codex subagent with the returned `agent_type` and prompt contents. If `may_use_skills` contains `ssrd` or another named skill, Main attaches or names that skill for the subagent.

## Usage: Codex CLI Bridge

```bash
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Optional env / CLI overrides:

| Variable / flag | Default | Purpose |
| --- | --- | --- |
| `CODEX_MODEL` / `--model` | `gpt-5.3-codex` | Model passed to `codex exec` |
| `CODEX_BIN` / `--codex-bin` | `codex` | Codex CLI binary |
| `CODEX_SANDBOX` / `--sandbox` | `workspace-write` | Sandbox mode |

## Manual Fallback

Use only when native subagents and CLI bridge are unavailable:

```bash
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

This writes `.codex-multi-agent/desktop-workers/*.prompt.md`.

## Result Contract

Every subagent must write:

- JSON result report under `.codex-multi-agent/results/`
- Markdown result report under `.codex-multi-agent/results/`
- `workspace_observed`, `required_paths_verified`, `files_read`, `files_changed`, and validation evidence

Main must run OpenClaw gate sync and scope audit before final delivery.

## What Works Today

- Native Codex skill install for App and CLI
- Bundled Codex custom agents under `~/.codex/agents`
- Native subagent prompt preparation
- CLI bridge via `codex exec`
- Manual prompt fallback
- Shared OpenClaw gate sync / audit

## Self-check

```bash
python3 scripts/install_native_skills.py --client codex --check
python3 adapters/codex/scripts/codex_self_check.py
```
