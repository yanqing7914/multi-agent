---
name: claude-code-multi-agent
description: Claude Code thin adapter for multi-agent coding. Use when Claude Code should run as a scoped Worker/Reviewer/Verifier with OpenClaw mission-control state, either via OpenClaw ACP runtime (sessions_spawn runtime=acp) or local claude --print one-shot workers. Do not use for unscoped full-repo edits without task cards.
---

# claude-code-multi-agent

Thin Claude Code adapter over the shared OpenClaw mission-control core.

## When To Use

Use when:

- Claude Code is the **execution agent** for a scoped task card
- you need the same preflight / result-report / gate contract as OpenClaw v1
- you run either **inside OpenClaw** (ACP) or **standalone** (local CLI)

## Two Launch Paths

### A) OpenClaw ACP (preferred inside OpenClaw)

When Main runs in OpenClaw/Her:

```text
sessions_spawn name="worker-backend" runtime="acp"
sessions_send session="worker-backend" message="<full task card>"
sessions_yield session="worker-backend"
```

Task cards already include `openclaw_handoff` blocks from `create_task_cards.py`. Set `runtime: acp` in YAML examples.

Print ACP handoff without spawning:

```bash
python3 adapters/claude-code/scripts/launch_claude_worker.sh \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --mode acp
```

### B) Local one-shot CLI (standalone)

Stateless worker when OpenClaw is not available:

```bash
python3 scripts/run_multi_agent.py \
  --runtime claude-code \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Runs:

```bash
claude --print --permission-mode bypassPermissions "<prompt with preflight + task card>"
```

Output teed to `.codex-multi-agent/results/<task_id>-<session>.md`.

## Role Mapping

| Role | ACP path | Local path |
| --- | --- | --- |
| Main | OpenClaw session or Claude Code project lead | Same |
| Worker | `runtime=acp` spawn | `launch_claude_worker.sh` |
| Reviewer | ACP spawn, read-only card | local `--print`, read-only card |
| Verifier | ACP spawn | local `--print` |

## Golden Path

1. Generate cards with `create_task_cards.py` (use `adapters/claude-code/examples/favorite-feature.yaml`).
2. Sync gates with `update_task_status.py --sync`.
3. Spawn via ACP **or** local launcher.
4. Audit with `audit_worker_output.py` — same as OpenClaw.

## Preflight & Result Report Contract

Same as OpenClaw v1 — see `adapters/openclaw/templates/result-report.md`.

## Shared Scripts

All mission-control scripts live under `adapters/openclaw/scripts/`.

## Validation

```bash
python3 adapters/claude-code/scripts/claude_code_self_check.py
python3 scripts/validate_all_adapters.py
```
