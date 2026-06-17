# Cursor Multi-Agent Adapter

Thin Cursor layer over [`adapters/openclaw/`](../openclaw/) mission-control
scripts. It does not duplicate task-card generation, gate sync, or audit logic.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## Install

No pip install. Python 3 only.

1. Use root `SKILL.md` / this folder's `SKILL.md` as Cursor project guidance for Main.
2. For Cursor Desktop, merge `.cursor/rules/multi-agent-coding.mdc` into the target workspace.
3. For automatic worker launch, ensure `agent` (Cursor CLI) and `tmux` are on PATH.
4. Generate `.codex-multi-agent/` state with OpenClaw's `create_task_cards.py`.

## Usage: Cursor Desktop

Use this path when the user is inside Cursor Desktop and wants a scoped Agent
prompt rather than tmux automation:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime cursor-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

This writes `.codex-multi-agent/cursor-desktop/*.cursor.md`. Open or paste the
prompt into Cursor Agent in the target workspace. The prompt requires the agent
to write JSON/Markdown result reports; Main then runs gate sync and scope audit.

This is not a separate Cursor-native subagent runtime. It is a Desktop-friendly
task-card prompt plus Cursor rules path.

## Usage: Cursor CLI Worker

From your target repo after generating task cards:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Direct launcher:

```bash
/path/to/multi-agent-coding/adapters/cursor/scripts/launch_cursor_worker.sh \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

### Expected output: tmux spawn

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

### Foreground debug

```bash
python3 adapters/cursor/scripts/launch_cursor_worker.py \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --foreground
```

Foreground mode waits for `agent` to finish, applies the same post-run checks
as Codex/Claude, and exits non-zero on failure.

## Contract

| Artifact | Location |
| --- | --- |
| Task cards | `.codex-multi-agent/tasks/*.md` |
| Result Markdown | `.codex-multi-agent/results/*.md` |
| Result JSON | `.codex-multi-agent/results/*.json` |
| Desktop prompts | `.codex-multi-agent/cursor-desktop/*.cursor.md` |
| Preflight | `adapters/openclaw/scripts/verify_workspace.py` |
| Schema | `adapters/openclaw/templates/result-report.md` |

## What Works Today

- Cursor Desktop prompt generation for scoped Agent sessions
- Cursor rules pack via `.cursor/rules/multi-agent-coding.mdc`
- Preflight via shared `verify_workspace.py` before spawn
- Prompt assembly with mandatory `cd` + result-report instructions
- tmux-detached `agent -p ... --force --trust --output-format text`
- Foreground mode with post-run checks
- Full gate/audit path via OpenClaw scripts when Main runs `--sync` / `audit_worker_output.py`

## Limitations

- Cursor Desktop mode is prompt/rules guided; it is not the same as Codex Desktop native subagent tools.
- tmux mode returns after spawning; Main must collect reports and sync gates.
- Automatic workers require local Cursor `agent` CLI and `tmux`.
- The adapter does not yet manage Cursor Background Agents or IDE task panels directly.

## Self-check

```bash
python3 adapters/cursor/scripts/cursor_self_check.py
```
