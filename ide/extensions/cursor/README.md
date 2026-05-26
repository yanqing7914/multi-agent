# Cursor extension scaffold (Phase 1)

Cursor-compatible VS Code extension skeleton that embeds the local mission-control panel.

## Differences from `ide/extensions/vscode/`

- Command id: `multiAgentCursor.openPanel`
- Opens beside the editor (`ViewColumn.Beside`)
- Honors `MULTI_AGENT_PANEL_URL` for non-default ports

## Usage

1. Start panel: `python3 ide/multi-agent-panel/server.py --state-dir .codex-multi-agent --port 9876`
2. Load this folder as an unpacked extension in Cursor (Developer: Install Extension from Location…)

**Not published** — complete TypeScript compile + signing before any marketplace submission.

See `ide/multi-agent-panel/README.md` and `ide/extensions/vscode/README.md` from the repository root.
