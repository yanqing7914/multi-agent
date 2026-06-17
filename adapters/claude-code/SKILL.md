---
name: claude-code-multi-agent
description: Claude Code-specific thin adapter for multi-agent coding. Use when Claude Code App/IDE or CLI should coordinate scoped Explorer/Worker/Reviewer/Verifier roles with native skills, bundled Claude subagents, task cards, result reports, and optional `claude --print` bridge. Do not use for simple single-agent edits.
---

# claude-code-multi-agent

Thin Claude Code adapter over the shared OpenClaw mission-control core.

## When To Use

Use when:

- Claude Code App/IDE or Claude Code CLI should participate in a scoped multi-agent workflow
- the user asks for Workers, Reviewers, Verifiers, parallel review, or review skills such as `ssrd`
- the task needs task cards, `allowed_paths`, result reports, and final audit
- Claude subagents should preload this skill and operate under explicit role boundaries

Do not use when:

- the task is a simple single-agent edit
- the task card is unscoped or lacks an output contract
- the user wants OpenClaw `sessions_spawn`; use `adapters/openclaw/`

## Execution Modes

| Mode | Use when | How |
| --- | --- | --- |
| Native Claude subagents | Claude Code App/IDE or CLI has loaded `.claude/agents` | Delegate to bundled Worker/Reviewer/Verifier agents |
| Claude Code CLI bridge | Script-launched local worker is desired | Run `scripts/run_multi_agent.py --runtime claude-code` |
| OpenClaw ACP | Main runs in OpenClaw/Her | Run `--runtime claude-code --mode acp` |
| Manual prompt fallback | Native subagents/CLI bridge are unavailable | Run `--runtime claude-desktop` |

## Golden Path

1. Install with `scripts/install_native_skills.py --client claude --scope primary --force`.
2. Reload Claude Code so it discovers `claude-code-multi-agent` and bundled agents.
3. Generate `.codex-multi-agent/` task cards.
4. Prefer native Claude subagents for Worker/Reviewer/Verifier roles.
5. Use CLI bridge only when Main wants deterministic script-launched workers:

```bash
python3 /path/to/claude-code-multi-agent/scripts/run_multi_agent.py \
  --runtime claude-code \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

6. Main runs gate sync and scope audit before final delivery.

## Skill Routing

- Reviewer cards may authorize `ssrd` with `may_use_skills: [ssrd]`.
- Bundled Reviewer/Verifier subagents are read-only by role.
- Worker subagents may edit only `allowed_paths` and may use only listed `may_use_skills`.
- If an authorized skill is unavailable, the subagent must report `status=blocked`.
- Skills cannot expand paths, shell commands, network access, credentials, git writes, or role permissions.

## Validation

```bash
python3 scripts/install_native_skills.py --client claude --check
python3 adapters/claude-code/scripts/claude_code_self_check.py
python3 scripts/validate_all_adapters.py
```
