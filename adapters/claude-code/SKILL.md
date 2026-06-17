---
name: claude-code-multi-agent
description: Claude Code / Claude Desktop adapter for multi-agent coding. Use Claude Desktop prompt mode for custom-skill/project users, OpenClaw ACP for orchestrated sessions, or Claude Code CLI for local one-shot workers.
---

# claude-code-multi-agent

Thin Claude adapter over the shared OpenClaw mission-control core.

## When To Use

Use when:

- Claude Code, Claude Desktop, or Claude.ai should participate in a scoped multi-agent workflow
- the user asks for Workers, Reviewers, parallel review, or review skills such as `ssrd`
- the task needs task cards, `allowed_paths`, result reports, and final audit

Do not use when:

- the task is a simple single-agent edit
- the user expects Claude Desktop mode to automatically mutate a local repo without tooling
- the task card is unscoped or lacks an output contract

## Execution Modes

| Mode | Use when | How |
| --- | --- | --- |
| Claude Desktop / Claude.ai prompt | User is in Claude Desktop or Claude.ai custom skill/project | Generate `.codex-multi-agent/claude-desktop/*.claude.md` |
| OpenClaw ACP | Main runs in OpenClaw/Her | Print `sessions_spawn` / `sessions_send` / `sessions_yield` handoff |
| Claude Code CLI | User has local `claude` CLI | Run `claude --print` one-shot worker |

## Golden Path

1. Generate `.codex-multi-agent/` task cards.
2. For Desktop users:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime claude-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

3. Use the prompt in Claude Desktop / Claude.ai custom skill context.
4. For automatic local edits, use `--runtime claude-code`.
5. For OpenClaw orchestration, use `--runtime claude-code --mode acp`.
6. Main runs gate sync and scope audit before final delivery.

## Skill Routing

- Reviewer cards may authorize `ssrd` with `may_use_skills: [ssrd]`.
- Claude Desktop prompts include authorized skill names; if unavailable, Claude must report blocked.
- Workers may not use skills to expand paths, shell commands, network access, credentials, git writes, or role permissions.

## Validation

```bash
python3 adapters/claude-code/scripts/claude_code_self_check.py
python3 scripts/validate_all_adapters.py
```
