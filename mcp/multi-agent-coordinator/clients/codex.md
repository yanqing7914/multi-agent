# Codex MCP registration

Configure in Codex MCP settings (UI or config file — same shape as other stdio MCP servers):

```json
{
  "mcpServers": {
    "multi-agent-coordinator": {
      "command": "python3",
      "args": [
        "/absolute/path/to/multi-agent-coding/mcp/multi-agent-coordinator/server.py",
        "--state-dir",
        "/absolute/path/to/your/workspace/.codex-multi-agent"
      ]
    }
  }
}
```

## Environment alternative

The server also honors `WORKSPACE`:

```bash
export WORKSPACE=/absolute/path/to/your/workspace
python3 /absolute/path/to/multi-agent-coding/mcp/multi-agent-coordinator/server.py
```

State resolves to `$WORKSPACE/.codex-multi-agent`.

## Codex worker launcher (non-MCP)

For spawning Workers via CLI:

```bash
python3 scripts/run_multi_agent.py --runtime codex --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

See [`../../../adapters/codex/QUICKSTART.md`](../../../adapters/codex/QUICKSTART.md).
