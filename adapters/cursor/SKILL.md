---
name: cursor-multi-agent
description: Cursor-specific thin adapter for multi-agent coding. Use when Cursor Main should spawn scoped Explorer/Worker/Reviewer/Verifier subagents via the Cursor agent CLI, with OpenClaw mission-control state (.codex-multi-agent/), preflight gates, and result-report contracts. Do not use for simple single-file edits or when OpenClaw session orchestration is already available.
---

# cursor-multi-agent

Thin Cursor adapter over the shared OpenClaw mission-control core. Reuses `adapters/openclaw/scripts/*` for task cards, gates, audits, and demos — this folder only maps Cursor spawn mechanics to that contract.

## When To Use

Use when:

- you are coordinating from **Cursor** as Main Agent
- the task needs Explorer / Worker / Reviewer / Verifier roles with path scoping
- you want `.codex-multi-agent/` local state, preflight, and false-completion gates
- you will spawn workers with the Cursor **`agent`** CLI (often inside **tmux**)

Do **not** use when:

- the task is a single quick edit (use Quick Path in root `SKILL.md`)
- you already run inside OpenClaw and prefer `sessions_spawn` — use `adapters/openclaw/` instead
- you need MCP-backed task panels (v2/v3 roadmap)

## Role Mapping (Cursor)

| Role | Cursor mechanism |
| --- | --- |
| Main | Current Cursor Agent session — runs `create_task_cards.py`, `--sync`, audit, delivery |
| Explorer | `agent -p "<task card>" --force --trust` in read-only card (`write_permission: false`) |
| Worker | `launch_cursor_worker.sh --task-card .codex-multi-agent/tasks/T00X-*.md` (tmux detached) |
| Reviewer | Same launcher; card sets `write_permission: false`, may authorize `ssrd` |
| Verifier | Same launcher; card lists validation commands |

Main stays accountable. Scripts update state; they do not spawn agents.

## Golden Path

1. **Generate mission-control state** (from target repo root):

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/multi-agent-coding/adapters/cursor/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

2. **Sync gates** before each wave:

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync
```

3. **Launch a worker** (preflight runs first; exits non-zero on failure):

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Or directly:

```bash
/path/to/multi-agent-coding/adapters/cursor/scripts/launch_cursor_worker.sh \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

4. **Attach to tmux** (if detached): `tmux attach -t cursor-T002`

5. **After each wave** — sync, capture diff, audit (same as OpenClaw):

```bash
git diff --name-only > .codex-multi-agent/changed-files.txt
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

## Preflight & Result Report Contract

Every worker prompt **starts with**:

```bash
cd "<absolute workspace_root from task card>"
pwd
python3 .../verify_workspace.py --workspace-root ... --required-paths ...
```

Workers must write **both**:

- Markdown: `.codex-multi-agent/results/<task_id>-<session>.md`
- JSON sidecar: same stem `.json` (schema: `adapters/openclaw/templates/result-report.md`)

The launcher tees CLI output to the Markdown path and best-effort extracts JSON from the log.

## Shared Scripts (do not duplicate)

| Script | Purpose |
| --- | --- |
| `adapters/openclaw/scripts/create_task_cards.py` | Task cards + ownership + status |
| `adapters/openclaw/scripts/update_task_status.py` | Gate sync + summarize |
| `adapters/openclaw/scripts/audit_worker_output.py` | Scope audit |
| `adapters/openclaw/scripts/verify_workspace.py` | Preflight path checks |
| `adapters/openclaw/scripts/run_local_demo.py` | Deterministic gate demo |

## Cursor-Specific Notes

- Requires **`agent`** CLI and **`tmux`** on PATH for detached workers.
- Use `--foreground` on `launch_cursor_worker.py` for debugging without tmux.
- Convert root `SKILL.md` rules into Cursor project rules for Main; this adapter covers **worker launch** only.
- `.codex-multi-agent/` is local/gitignored — do not commit unless the user asks.

## Validation

```bash
python3 adapters/cursor/scripts/cursor_self_check.py
python3 scripts/validate_all_adapters.py
```
