# Claude Multi-Agent Adapter

Thin Claude Code / Claude Desktop layer over [`adapters/openclaw/`](../openclaw/)
mission-control scripts.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## Install

No pip install. Python 3 only.

1. For Claude Code projects, merge bundled `CLAUDE.md` into the target project instructions.
2. For Claude Desktop / Claude.ai, use the generated prompt inside a custom skill or project/chat context.
3. For automatic local edits, install and authenticate Claude Code CLI (`claude`).
4. For OpenClaw/Her, prefer ACP handoff mode.

## Usage: Claude Desktop / Claude.ai Skill Prompt

Use this when the user is inside Claude Desktop or Claude.ai and wants a scoped
task-card prompt rather than CLI automation:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime claude-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

This writes `.codex-multi-agent/claude-desktop/*.claude.md`. Use the prompt in
Claude Desktop / Claude.ai custom skill context or paste it into a Claude
project/chat that has access to the repository tooling.

This is not an automatic desktop worker launcher. For automatic local repo
edits, use Claude Code CLI. For OpenClaw session orchestration, use ACP.

## Usage: OpenClaw ACP

```bash
python3 adapters/claude-code/scripts/launch_claude_worker.sh \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --mode acp
```

Prints spawn/send/yield handoff JSON. Main pastes the task card into
`sessions_send`.

## Usage: Claude Code CLI

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime claude-code \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Runs:

```text
claude --print --permission-mode bypassPermissions "<preflight + task card prompt>"
```

On failure (non-zero CLI exit, 429/budget/quota/`Request rejected` in log,
missing artifacts), the launcher prints `"ok": false` and exits non-zero.

## Contract

| Artifact | Location |
| --- | --- |
| Task cards | `.codex-multi-agent/tasks/*.md` |
| Result Markdown | `.codex-multi-agent/results/*.md` |
| Result JSON | `.codex-multi-agent/results/*.json` |
| Desktop prompts | `.codex-multi-agent/claude-desktop/*.claude.md` |
| Schema | `adapters/openclaw/templates/result-report.md` |

## What Works Today

- Claude Desktop / Claude.ai custom-skill prompt generation
- Claude Code project instructions via bundled `CLAUDE.md`
- Preflight before local `claude --print`
- ACP handoff JSON for OpenClaw Main
- Shared gate/audit via OpenClaw scripts
- Result tee + JSON extraction helper

## Limitations

- Claude Desktop mode is prompt/skill guided; it does not automatically spawn local CLI workers.
- Local Claude Code CLI can hit HTTP 429 / budget limits; the launcher reports `quota_exhausted`.
- `bypassPermissions` is powerful; use only on trusted scoped tasks.
- Claude Code session features beyond `--print` are not wrapped yet.

## Self-check

```bash
python3 adapters/claude-code/scripts/claude_code_self_check.py
```
