# Cursor MCP registration

Register the multi-agent coordinator in Cursor's MCP config (`.cursor/mcp.json` or **Settings → MCP**).

Replace `/absolute/path/to/multi-agent-coding` and `/absolute/path/to/your/workspace` with your paths.

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

## Optional: workspace-relative state dir

If Cursor launches MCP with cwd set to your project root:

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

## Verify

```bash
python3 mcp/multi-agent-coordinator/scripts/self_check.py
```

See [`../README.md`](../README.md).
