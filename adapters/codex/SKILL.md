---
name: codex-multi-agent
description: Codex-specific thin adapter for multi-agent coding. Use when Codex Main should delegate scoped Explorer/Worker/Reviewer/Verifier roles via native Codex Desktop subagents first, with Desktop prompt handoff or `codex exec` as fallbacks. Do not use for trivial single-agent coding without task cards.
---

# codex-multi-agent

Thin Codex adapter over the shared OpenClaw mission-control core. Reuses
`adapters/openclaw/scripts/*` for task cards, gates, audits, and demos.

## When To Use

Use when:

- you are coordinating from Codex as Main Agent
- the user explicitly asks for multiple agents, subagents, workers, reviewers, or parallel review
- the task needs role ownership, path boundaries, result reports, and final diff audit
- Workers should run via native Codex Desktop subagents, Desktop handoff, or `codex exec`

Do not use when:

- a single Codex session can finish the task cleanly
- the user did not ask for subagents or parallel agent work
- you need OpenClaw session-yield semantics; use `adapters/openclaw/`

## Execution Modes

| Mode | Priority | Use when | How |
| --- | --- | --- | --- |
| Native Desktop subagents | 1 | Codex Desktop exposes subagent tools | Main spawns `explorer` / `worker` subagents with task-card prompts |
| Desktop prompt handoff | 2 | Native spawn tools are unavailable | Generate `.codex-multi-agent/desktop-workers/*.prompt.md` |
| CLI auto-run | 3 | User has Codex CLI installed | Launch `codex exec` with preflight and result-report checks |

Native Desktop subagents are the target UX. Handoff prompts are only a fallback
for Desktop builds or clients that cannot expose subagent tools to the Main
agent.

## Native Desktop Subagent Contract

Codex Desktop can run subagent workflows when the current app exposes subagent
tools and the user explicitly requests delegation. The Main agent must:

1. Generate task cards and ownership metadata under `.codex-multi-agent/`.
2. For each task card, prepare a native spawn prompt:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex-native \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

3. Read the returned `prompt_path`.
4. Spawn a native subagent with the returned `agent_type` and prompt contents.
5. Attach or name only skills listed in `may_use_skills`.
6. Wait for the subagent result, then run gate sync and scope audit.
7. Close completed subagents when their results are integrated.

Role mapping:

| Task role | Codex native agent type | Write policy |
| --- | --- | --- |
| Explorer | `explorer` | read-only |
| Reviewer | `explorer` | read-only; may use review skills such as `ssrd` only if authorized |
| Verifier | `explorer` | read-only validation |
| Worker | `worker` | scoped writes within `allowed_paths` |

Workers must not spawn child agents unless the task card explicitly says
`may_spawn_sessions: true`. Even then, child agents inherit the Worker's scope
and should normally be read-only Explorers.

## Skill Use Routing

Task cards control skill use with `may_use_skills`.

- If the user says "open multiple agents to review with ssrd", create Reviewer
  task cards with `may_use_skills: [ssrd]` and `write_permission: false`.
- When spawning a native Codex subagent, include the named skill in the prompt
  and attach it as a skill item if the client supports structured skill input.
- If the skill is unavailable inside the subagent, the subagent must report
  `status=blocked`; it must not silently replace it with a different method.
- Workers may use only task-card skills and cannot use skills to expand file,
  shell, network, credential, git, or role permissions.

## Fallback: Desktop Prompt Handoff

Use this only when native subagent tools are unavailable:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Open the returned `prompt_path` in a separate Codex Desktop session or task.
The Worker must write both result reports listed in the prompt.

## Fallback: CLI Worker

Use this when Codex CLI is available and the user wants script-launched workers:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Optional environment overrides:

- `CODEX_MODEL`: default `gpt-5.3-codex`
- `CODEX_BIN`: default `codex`
- `CODEX_SANDBOX`: default `workspace-write`

## Golden Path

1. Generate `.codex-multi-agent/` task cards from YAML or CLI args.
2. Sync gates with `update_task_status.py --sync`.
3. Prefer native Desktop subagents via `--runtime codex-native`.
4. Use Desktop handoff or CLI auto-run only as fallback.
5. Require every subagent to write JSON and Markdown result reports.
6. Run scope audit before final delivery.

## Validation

```bash
python3 adapters/codex/scripts/codex_self_check.py
python3 scripts/validate_all_adapters.py
```
