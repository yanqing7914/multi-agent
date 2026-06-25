# Claude Code Multi-Agent Adapter

Thin Claude Code layer over [`adapters/openclaw/`](../openclaw/) mission-control scripts.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## What This Enables

Claude Code App/IDE and Claude Code CLI both get:

1. A native `claude-code-multi-agent` skill.
2. Bundled Claude subagents for Worker, Reviewer, and Verifier roles.
3. Shared task cards and result-report contracts under `.codex-multi-agent/`.
4. Optional `claude --print` bridge for script-launched one-shot workers.
5. OpenClaw ACP handoff when Claude participates inside Her/OpenClaw.
6. Optional Claude Agent Teams orchestration (experimental) mapped to task cards, ownership boundaries, and the scope-audit gate — see [TEAMS.md](TEAMS.md).

Manual prompt generation remains available, but v0.3.1 treats native Claude Code skills + subagents as the full App/CLI path.

## Install

From the extracted `claude-code-multi-agent-pack-v0.3.1.zip` root:

```bash
python3 scripts/install_native_skills.py --client claude --scope primary --force
python3 scripts/install_native_skills.py --client claude --check
```

The installer writes:

```text
~/.claude/skills/claude-code-multi-agent
~/.agents/skills/claude-code-multi-agent
~/.claude/agents/multi-agent-worker.md
~/.claude/agents/multi-agent-reviewer.md
~/.claude/agents/multi-agent-verifier.md
```

## Usage: Native Claude Code Subagents

Ask Claude Code:

```text
Use claude-code-multi-agent. Split this task into scoped task cards, delegate Worker/Reviewer/Verifier roles to the bundled subagents, require JSON and Markdown reports, then audit the diff before final delivery.
```

Reviewer cards may include `may_use_skills: [ssrd]`; the Reviewer subagent may use only those listed skills.

## Usage: Claude Code CLI Bridge

For deterministic script-launched Workers:

```bash
python3 /path/to/claude-code-multi-agent/scripts/run_multi_agent.py \
  --runtime claude-code \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

The launcher runs `claude --print` with preflight and result-report checks. It reports quota/budget failures as non-zero instead of pretending the task completed.

## Usage: OpenClaw ACP

```bash
python3 /path/to/claude-code-multi-agent/scripts/run_multi_agent.py \
  --runtime claude-code \
  --mode acp \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Main uses the printed `sessions_spawn` / `sessions_send` / `sessions_yield` handoff in OpenClaw/Her.

## Manual Fallback

Use only when native subagents and CLI bridge are unavailable:

```bash
python3 /path/to/claude-code-multi-agent/scripts/run_multi_agent.py \
  --runtime claude-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

This writes `.codex-multi-agent/claude-desktop/*.claude.md`.

## Contract

| Artifact | Location |
| --- | --- |
| Task cards | `.codex-multi-agent/tasks/*.md` |
| Result Markdown | `.codex-multi-agent/results/*.md` |
| Result JSON | `.codex-multi-agent/results/*.json` |
| Manual prompts | `.codex-multi-agent/claude-desktop/*.claude.md` |
| Schema | `adapters/openclaw/templates/result-report.md` |

## Self-check

```bash
python3 scripts/install_native_skills.py --client claude --check
python3 adapters/claude-code/scripts/claude_code_self_check.py
```
