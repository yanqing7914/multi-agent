# Cursor Multi-Agent Adapter

Thin Cursor layer over [`adapters/openclaw/`](../openclaw/) mission-control scripts. Does **not** duplicate task-card generation, gate sync, or audit logic.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## Install

No pip install. Python 3 only.

1. Use root `SKILL.md` / this folder's `SKILL.md` as Cursor project guidance for Main.
2. Ensure **`agent`** (Cursor CLI) and **`tmux`** are on PATH for worker launch.
3. Generate `.codex-multi-agent/` state with OpenClaw's `create_task_cards.py`.

## Usage

From your **target repo** after generating task cards:

```bash
# Dispatch via cross-adapter entrypoint
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md

# Or call launcher directly
/path/to/multi-agent-coding/adapters/cursor/scripts/launch_cursor_worker.sh \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

### Expected output (success preflight + tmux spawn)

```json
{
  "ok": true,
  "runtime": "cursor",
  "mode": "tmux",
  "tmux_session": "cursor-T002",
  "workspace_root": "/path/to/target-repo",
  "result_markdown": "/path/to/target-repo/.codex-multi-agent/results/T002-worker-backend.md",
  "attach": "tmux attach -t cursor-T002"
}
```

### Expected output (preflight failure)

Exit code `2`. JSON includes `"stage": "preflight"` and `"ok": false`. Worker is **not** spawned.

### Foreground debug (no tmux)

```bash
python3 adapters/cursor/scripts/launch_cursor_worker.py \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --foreground
```

Foreground mode waits for `agent` to finish, applies the same post-run checks as Codex/Claude (non-trivial Markdown, JSON file or extracted sidecar, log error patterns), and exits non-zero on failure.

### tmux fire-and-forget caveat

Default tmux mode returns `"ok": true` immediately after spawning the session. The launcher does **not** wait for `agent` to finish. Main must poll `result_markdown` / `result_json` and run gate sync only after artifacts exist. Use `--foreground` when debugging launcher failure semantics.

## Contract

| Artifact | Location |
| --- | --- |
| Task cards | `.codex-multi-agent/tasks/*.md` |
| Result Markdown | `.codex-multi-agent/results/*.md` |
| Result JSON | `.codex-multi-agent/results/*.json` |
| Preflight | `adapters/openclaw/scripts/verify_workspace.py` |
| Schema | `adapters/openclaw/templates/result-report.md` |

## Self-check

```bash
python3 adapters/cursor/scripts/cursor_self_check.py
```

Validates launcher executable, docs, examples, and OpenClaw script/template presence. Does **not** run `agent`.

## What works today

- Preflight via shared `verify_workspace.py` before spawn
- Prompt assembly with mandatory `cd` + result-report instructions
- tmux-detached `agent -p ... --force --trust --output-format text`
- Tee to agreed Markdown result path
- Best-effort JSON extraction from worker log
- Full gate/audit path via OpenClaw scripts when Main runs `--sync` / `audit_worker_output.py`

## Limitations

- Does not auto-attach tmux or poll for completion — Main must collect reports and sync gates.
- tmux mode does not validate worker completion at launch time (spawn-only `ok: true`).
- Requires local Cursor `agent` CLI; not validated in CI.
- No IDE task panel (v3 roadmap).
