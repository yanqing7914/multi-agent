# OpenClaw / ACP wiring

OpenClaw v1 uses **skill + sessions** as the primary path; MCP is optional glue on the same `.codex-multi-agent/` state.

## Option A — Skill only (recommended v1)

1. Install [`adapters/openclaw/`](../../../adapters/openclaw/) as skill `openclaw-multi-agent`.
2. Generate cards:

   ```bash
   python3 adapters/openclaw/scripts/create_task_cards.py \
     --from-yaml adapters/openclaw/examples/favorite-feature.yaml \
     --out .codex-multi-agent \
     --workspace-root "$(pwd)"
   ```

3. Main uses `sessions_spawn` / `sessions_send` with task card content (see card `openclaw_handoff` blocks).

## Option B — MCP + OpenClaw sessions

Register MCP so Main can call `create_task`, `update_task_status`, `audit_scope` without shelling to scripts:

```json
{
  "mcpServers": {
    "multi-agent-coordinator": {
      "command": "python3",
      "args": [
        "/absolute/path/to/multi-agent-coding/mcp/multi-agent-coordinator/server.py",
        "--state-dir",
        ".codex-multi-agent"
      ],
      "cwd": "/absolute/path/to/your/workspace"
    }
  }
}
```

## ACP session flow

```text
Main → create_task_cards (or MCP create_task)
     → sessions_spawn(Worker, task_card_path)
     → Worker writes results/*.json
     → update_task_status --sync
     → audit_worker_output --write-audit
     → update_task_status --summarize
```

## Normalized worker outcomes

OpenClaw ACP session logs should be checked with `adapters/_shared/worker_outcome.py` patterns (`quota_exhausted`, `timeout`, etc.) before marking `workers_complete`.

## Verify

```bash
python3 adapters/openclaw/scripts/validate_all.py
python3 mcp/multi-agent-coordinator/scripts/self_check.py
```
