---
name: codex-multi-agent
description: Codex-specific thin adapter for multi-agent coding. Use when Codex Main should delegate scoped Explorer/Worker/Reviewer/Verifier roles via `codex exec`, with OpenClaw mission-control state, preflight gates, and result-report contracts. Do not use for trivial single-agent coding without task cards.
---

# codex-multi-agent

Thin Codex adapter over the shared OpenClaw mission-control core. Reuses `adapters/openclaw/scripts/*` for task cards, gates, audits, and demos.

## When To Use

Use when:

- you are coordinating from **Codex** as Main Agent (this repo as a skill)
- the task needs multi-role collaboration with path ownership
- workers should run via **`codex exec`** (default model `gpt-5.3-codex`, overridable)
- you want the same `.codex-multi-agent/` contract as OpenClaw v1

Do **not** use when:

- a single Codex session can finish the task (Quick Path)
- you need OpenClaw session yield semantics — use `adapters/openclaw/`

## Role Mapping (Codex)

| Role | Codex mechanism |
| --- | --- |
| Main | Codex session with `$multi-agent-coding` — runs mission-control scripts |
| Explorer / Reviewer / Verifier | `codex exec` with read-only task card |
| Worker | `launch_codex_worker.sh --task-card ...` |

## Golden Path

1. **Generate state** (target repo root):

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/multi-agent-coding/adapters/codex/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

2. **Sync gates**:

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync
```

3. **Launch worker** (preflight enforced; non-zero exit on failure):

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Environment overrides (optional, not required in scripts):

- `CODEX_MODEL` — default `gpt-5.3-codex`
- `CODEX_BIN` — default `codex`
- API keys: configure via Codex CLI / user environment (never commit secrets)

4. **Parallel workers** — use **git worktrees** (one checkout per Worker):

```bash
git worktree add ../feature-backend -b worker/backend
cd ../feature-backend
# generate cards with --workspace-root "$(pwd)" or share one state dir carefully
CODEX_WORKTREE=../feature-backend launch_codex_worker.sh --task-card ...
```

5. **Audit & summarize** — same OpenClaw scripts as Golden Path step 5–7 in `adapters/openclaw/QUICKSTART.md`.

## Preflight & Result Report Contract

Identical to OpenClaw v1:

- Mandatory `cd` + `verify_workspace.py` before work
- JSON + Markdown under `.codex-multi-agent/results/`
- Gates block false completion and thin evidence

## Shared Scripts

Same table as `adapters/cursor/SKILL.md` — all under `adapters/openclaw/scripts/`.

## Validation

```bash
python3 adapters/codex/scripts/codex_self_check.py
python3 scripts/validate_all_adapters.py
```
