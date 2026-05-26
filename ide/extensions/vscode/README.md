# VS Code extension scaffold (Phase 1)

**Not published to the marketplace.** This folder is a starting point for embedding the mission-control panel in VS Code.

## Phase 1 behavior

1. User starts the stdlib panel server:

   ```bash
   python3 ide/multi-agent-panel/server.py --state-dir .codex-multi-agent --port 9876
   ```

2. Extension command **Open Multi-Agent Panel** loads `http://127.0.0.1:9876/` inside a VS Code webview (`extension.ts`).

## Files

| File | Purpose |
| --- | --- |
| `package.json` | Minimal extension manifest |
| `extension.ts` | Webview iframe to local panel |

## Next steps (not implemented)

- Auto-start panel server from extension host
- Task board commands bound to MCP tools
- Publish workflow / marketplace listing

See `ide/multi-agent-panel/README.md` from the repository root.
