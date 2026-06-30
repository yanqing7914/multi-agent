---
name: codex-multi-agent
description: Codex-specific thin adapter for multi-agent coding. Use when Codex App or Codex CLI should delegate scoped Explorer/Worker/Reviewer/Verifier roles with native Codex skills, bundled custom agents, task cards, result reports, and optional `codex exec` bridge. Do not use for trivial single-agent coding without task cards.
---

# codex-multi-agent

Thin Codex adapter over the shared OpenClaw mission-control core. Reuse
`adapters/openclaw/scripts/*` for task cards, gates, audits, and demos.
When installed inside the full `multi-agent` package, this adapter powers the
root `multi-agent-coding` Codex fast path; users can trigger either name, but
the product goal is that `multi-agent` works as the Codex daily entrypoint.

## When To Use

Use when:

- coordinating from Codex App or Codex CLI as Main Agent
- the user explicitly asks for multiple agents, subagents, Workers, Reviewers, Verifiers, or parallel review
- the task needs role ownership, path boundaries, result reports, and final diff audit
- Codex should use native subagents or the optional `codex exec` bridge

Do not use when:

- a single Codex session can finish the task cleanly
- the user did not ask for subagents or parallel agent work
- you need OpenClaw session-yield semantics; use `adapters/openclaw/`

## Execution Modes

| Mode | Priority | Use when | How |
| --- | --- | --- | --- |
| Native Codex subagents | 1 | Codex App/CLI supports subagent workflows | Main spawns scoped Worker/Reviewer/Verifier agents with task-card prompts |
| Codex custom agents | 1 | Bundled `.toml` agents are installed | Use `multi-agent-worker` and `multi-agent-reviewer` definitions |
| CLI bridge | 2 | User wants script-launched workers | Run `scripts/run_multi_agent.py --runtime codex` |
| Manual handoff fallback | 3 | Native subagents and CLI bridge are unavailable | Run `--runtime codex-desktop` |

## Native Subagent Contract

For the complete machine-readable App routine, read
`adapters/codex/NATIVE_SUBAGENT_CONTRACT.md` before spawning subagents.

Codex App and Codex CLI can run subagent workflows when the user explicitly requests delegation. Main must:

1. Generate task cards and ownership metadata under `.codex-multi-agent/`.
2. For normal App use, prepare a full native spawn plan:

```bash
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex-native-plan \
  --state-dir .codex-multi-agent
```

3. Spawn one native subagent per plan record with `spawn_agent_payload`.
4. For a single task card, prepare one native spawn prompt:

```bash
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex-native \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

5. Attach or name only skills listed in `may_use_skills`; `spawn_agent_payload.items` carries skill items when available.
6. Wait for JSON and Markdown result reports.
7. Run gate sync and scope audit before final delivery.

Role mapping:

| Task role | Codex agent type | Write policy |
| --- | --- | --- |
| Explorer | `explorer` | read-only |
| Reviewer | `multi-agent-reviewer` or `explorer` | read-only; may use review skills such as `ssrd` only if authorized |
| Verifier | `explorer` | read-only validation |
| Worker | `multi-agent-worker` or `worker` | scoped writes within `allowed_paths` |

Workers must not spawn child agents unless the task card explicitly says
`may_spawn_sessions: true`. Child agents inherit the Worker's scope and should
normally be read-only Explorers.

> Reliable custom `agent_type` selection (e.g. `multi-agent-reviewer`'s read-only
> sandbox) requires Codex CLI >= 0.139.0. On older versions `spawn_agent` ignores
> the custom type and falls back to a generic subagent; the role, write-permission,
> and read-only instructions embedded in the prompt still enforce the boundary.

## Skill Use Routing

Task cards control skill use with `may_use_skills`.

- If the user says "open multiple agents to review with ssrd", create Reviewer task cards with `may_use_skills: [ssrd]` and `write_permission: false`.
- Include authorized skills in the subagent prompt and attach them if the client supports structured skill input.
- If an authorized skill is unavailable inside the subagent, the subagent must report `status=blocked`.
- Workers may use only task-card skills and cannot use skills to expand file, shell, network, credential, git, or role permissions.

## CLI Bridge

Use this when Codex CLI is available and Main wants script-launched workers:

```bash
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Optional environment overrides:

- `CODEX_MODEL`: default `gpt-5.3-codex`
- `CODEX_BIN`: default `codex`
- `CODEX_SANDBOX`: default `workspace-write`

## Manual Fallback

Use only when native subagents and CLI bridge are unavailable:

```bash
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Open the returned `prompt_path` in a separate Codex App session or task. The Worker must write both result reports listed in the prompt.

## Golden Path

1. Install with `scripts/install_native_skills.py --client codex --scope primary --force`.
2. Run `python adapters/codex/scripts/doctor_codex.py` or `python scripts/doctor.py --client codex`.
3. Reload Codex so it discovers the `multi-agent` / `codex-multi-agent` entry and custom agents.
4. Generate `.codex-multi-agent/` task cards from YAML or CLI args.
5. Prefer native Codex subagents via `--runtime codex-native-plan`.
6. Use CLI bridge when deterministic script launch is desired.
7. Require every subagent to write JSON and Markdown result reports.
8. Run scope audit before final delivery.

## Validation

```bash
python3 scripts/install_native_skills.py --client codex --check
python3 adapters/codex/scripts/doctor_codex.py
python3 adapters/codex/scripts/codex_self_check.py
python3 scripts/validate_all_adapters.py
```
