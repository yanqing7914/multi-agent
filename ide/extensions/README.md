# IDE extension build checks

This directory contains local-only VS Code-compatible extension scaffolds for opening the multi-agent panel in an editor webview.

## Build both extensions

```bash
ide/extensions/scripts/build_check.sh
```

The script exits successfully with a skip message when `node` or `npm` is unavailable. When Node tooling is present, it runs `npm install`, `npm run compile`, and `npx --no-install vsce package --no-dependencies` for both `vscode` and `cursor`.

## Build one extension manually

```bash
cd ide/extensions/vscode
npm install
npm run compile
npx --no-install vsce package --no-dependencies
```

Use `ide/extensions/cursor` for the Cursor-flavored package. Generated `.vsix` archives are local artifacts and are ignored by git.

## Install locally

1. Start the panel server from the repository root:

   ```bash
   python3 ide/multi-agent-panel/server.py --state-dir .codex-multi-agent --port 9876
   ```

2. Package the extension with the commands above.
3. In VS Code or Cursor, run `Extensions: Install from VSIX...` and choose the generated `.vsix`.
4. Run `Open Multi-Agent Panel` in VS Code or `Cursor: Open Multi-Agent Panel` in Cursor.

These extensions are not published to any marketplace.
