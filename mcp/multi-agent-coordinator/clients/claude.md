# Claude Code MCP registration

Add to Claude Code MCP settings (`~/.claude/settings.json` or project `.mcp.json` depending on your install):

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

## Notes

- **`cwd` is required** when using a relative `--state-dir`.
- Claude Code sessions should still follow task cards for Explorer/Worker/Reviewer/Verifier roles; MCP stores state only.
- On quota/429 errors, prefer OpenClaw ACP path — see [`../../../adapters/claude-code/QUICKSTART.md`](../../../adapters/claude-code/QUICKSTART.md).

## Verify

```bash
python3 mcp/multi-agent-coordinator/scripts/self_check.py
```
