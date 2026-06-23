---
name: cursor-multi-agent
description: Cursor-specific thin adapter for multi-agent coding. Use when Cursor App or Cursor CLI should coordinate scoped Explorer/Worker/Reviewer/Verifier roles with native Cursor Agent Skills, task cards, result reports, and a local `agent` CLI bridge for automatic Workers. Do not use for simple single-agent edits.
---

# cursor-multi-agent

Thin Cursor adapter over the shared OpenClaw mission-control core. Reuse
`adapters/openclaw/scripts/*` for task cards, gates, audits, and demos.

## When To Use

Use when:

- coordinating from Cursor App or Cursor CLI as Main Agent
- the user asks for multiple agents, Workers, Reviewers, Verifiers, or parallel review
- the task needs scoped `allowed_paths`, `blocked_commands`, result reports, and final diff audit
- Cursor should use native Agent Skills plus the local `agent` CLI bridge for automatic Workers

Do not use when:

- the task is a quick single-agent edit
- the user wants OpenClaw `sessions_spawn`; use `adapters/openclaw/`
- `agent` CLI is missing and the user requires automatic Worker execution with no manual handoff

## Execution Modes

| Mode | Use when | How |
| --- | --- | --- |
| Native Cursor skill | Cursor App or CLI has loaded this skill | Main follows this workflow and creates task cards |
| App native parallel | Inside Cursor 3 App | Use `/multitask` (parallel subagents, each in its own worktree/PR) or `/sdk`; see `SDK.md` |
| Cursor SDK / headless | Programmatic or CI runs | `@cursor/sdk` or headless `agent -p --output-format json`; generate run specs with `scripts/prepare_cursor_sdk.py`; see `SDK.md` |
| Cursor CLI bridge | Automatic Workers from a script | Run `scripts/run_multi_agent.py --runtime cursor` (deterministic scripted/CI path) |
| Manual handoff fallback | `agent` CLI is unavailable | Run `--runtime cursor-desktop` and paste/open prompts in Cursor Agent |

Cursor App supports native Agent Skills. Cursor 3's Agents Window (`/multitask`,
`/worktree`) and the Cursor SDK provide native parallel subagents; this adapter's
current automation path for complete Worker orchestration is the local Cursor
`agent` CLI bridge (native in-App `/multitask` integration is on the roadmap),
which stays the deterministic path for scripted/CI runs.

## Golden Path

1. Install the package with `scripts/install_native_skills.py --client cursor --scope primary --force`.
2. Restart/reload Cursor so it discovers `cursor-multi-agent`.
3. Generate `.codex-multi-agent/` task cards from the target repo.
4. Check bridge readiness with `scripts/install_native_skills.py --client cursor --check` (or the friendlier `scripts/doctor.py --client cursor`). The bridge needs the Cursor CLI on PATH: `agent` (or legacy alias `cursor-agent`), installable via `curl https://cursor.com/install -fsS | bash` (Windows: `irm 'https://cursor.com/install?win32=true' | iex`).
5. For full automatic Workers, launch:

```bash
python3 /path/to/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

6. For synchronous debugging, add `--foreground`.
7. If `agent` is unavailable, use `--runtime cursor-desktop` only as a manual fallback.
8. Main runs gate sync and scope audit before delivery.

## Skill Routing

- Reviewer cards may authorize review skills such as `ssrd` with `may_use_skills: [ssrd]`.
- Worker cards may authorize implementation skills only when the user or Main explicitly allows them.
- Authorized skill names must be included in the Worker/Reviewer prompt.
- If an authorized skill is unavailable, the agent must report `status=blocked`.
- Workers may not use skills to expand paths, shell commands, network access, credentials, git writes, or role permissions.

## Validation

```bash
python3 scripts/install_native_skills.py --client cursor --check
python3 scripts/doctor.py --client cursor
python3 adapters/cursor/scripts/cursor_self_check.py
python3 scripts/validate_all_adapters.py
```
