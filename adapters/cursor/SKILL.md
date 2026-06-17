---
name: cursor-multi-agent
description: Cursor-specific adapter for multi-agent coding. Use Cursor Desktop prompt/rules mode first for desktop users, or Cursor agent CLI/tmux for automatic Workers. Do not use for simple single-file edits.
---

# cursor-multi-agent

Thin Cursor adapter over the shared OpenClaw mission-control core. Reuses
`adapters/openclaw/scripts/*` for task cards, gates, audits, and demos.

## When To Use

Use when:

- you are coordinating from Cursor as Main Agent
- the user asks for multiple agents, Workers, Reviewers, or parallel review
- the task needs scoped `allowed_paths`, result reports, and final diff audit
- Cursor Desktop should receive task-card prompts, or Cursor CLI should launch background workers

Do not use when:

- the task is a quick single-agent edit
- the user wants OpenClaw `sessions_spawn`; use `adapters/openclaw/`
- the user expects Cursor Desktop to expose Codex-style native subagent tools

## Execution Modes

| Mode | Use when | How |
| --- | --- | --- |
| Cursor Desktop prompt | User is in Cursor Desktop | Generate `.codex-multi-agent/cursor-desktop/*.cursor.md` and paste/open in Cursor Agent |
| Cursor CLI worker | User has `agent` CLI + `tmux` | Run `scripts/run_multi_agent.py --runtime cursor` |

Cursor Desktop mode is not a separate native subagent runtime. It is a
Desktop-friendly prompt/rules path that preserves the same task-card, result,
and audit contract.

## Golden Path

1. Install or merge `.cursor/rules/multi-agent-coding.mdc` into the target workspace.
2. Generate `.codex-multi-agent/` task cards.
3. Prefer `--runtime cursor-desktop` for Desktop users:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime cursor-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

4. Paste/open the generated prompt in Cursor Agent.
5. Use `--runtime cursor` only when CLI/tmux automation is desired.
6. Main runs gate sync and scope audit before delivery.

## Skill Routing

- Reviewer cards may authorize review skills such as `ssrd` with `may_use_skills: [ssrd]`.
- Cursor Desktop prompts include authorized skill names; if unavailable, the Agent must report blocked.
- Workers may not use skills to expand paths, shell commands, network access, credentials, git writes, or role permissions.

## Validation

```bash
python3 adapters/cursor/scripts/cursor_self_check.py
python3 scripts/validate_all_adapters.py
```
