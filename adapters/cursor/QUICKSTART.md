# Cursor Multi-Agent — Quickstart

Dependency-free Python 3. Reuses OpenClaw mission-control scripts.

## 1. Generate task cards

From **target repo root**:

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/multi-agent-coding/adapters/cursor/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

## 2. Validate bridge (no agents)

```bash
python3 /path/to/multi-agent-coding/adapters/cursor/scripts/cursor_self_check.py
python3 /path/to/multi-agent-coding/scripts/validate_all_adapters.py
```

Expected: `"ok": true` JSON, exit `0`.

## 3. Launch a worker

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Attach: `tmux attach -t cursor-T002`

**tmux caveat:** Launch returns after spawn; poll result files before `--sync`. For synchronous validation, add `--foreground` to `launch_cursor_worker.py`.

## 4. Sync gates & audit

Same as [OpenClaw QUICKSTART](../openclaw/QUICKSTART.md) steps 5–7.

## 5. Local demo (no Cursor CLI)

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/run_local_demo.py --self-check
```
