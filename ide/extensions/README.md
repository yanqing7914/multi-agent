# IDE extension build checks

This directory contains local-only VS Code-compatible extension scaffolds for opening the multi-agent panel in an editor webview.

## Build both extensions

```bash
ide/extensions/scripts/build_check.sh
```

The script exits successfully with a skip message when `node` or `npm` is unavailable. When Node tooling is present, it runs `npm ci` and `npx tsc --noEmit -p .` for both `vscode` and `cursor`.

## Build one extension manually

```bash
cd ide/extensions/vscode
npm install
npm run compile
npx --no-install vsce package --no-dependencies
```

Use `ide/extensions/cursor` for the Cursor-flavored package. Generated `.vsix` archives are local artifacts and are ignored by git.

> **图标占位**：`package.json` 中 `icon` 指向 `images/icon.png`（文件可尚未提交）；发布前请添加 128×128 PNG，详见 [PUBLISHING.md](./PUBLISHING.md)。

## 发布到 Marketplace

发布前请将两个扩展 `package.json` 里的 `<PUBLISHER_TBD>` 替换为你在 Marketplace / OpenVSX 注册的 publisher ID，并配置 PAT：

- 完整 SOP（注册 publisher、Azure PAT、OpenVSX token、排错）：[PUBLISHING.md](./PUBLISHING.md)
- 一键打包 / 发布脚本：[scripts/publish.sh](./scripts/publish.sh)

```bash
# 仅打包
EXTENSION=vscode ./ide/extensions/scripts/publish.sh

# 有 token 时发布
EXTENSION=vscode VSCE_PAT="$VSCE_PAT" OVSX_PAT="$OVSX_PAT" ./ide/extensions/scripts/publish.sh
```

## Install locally

1. Start the panel server from the repository root:

   ```bash
   python3 ide/multi-agent-panel/server.py --state-dir .codex-multi-agent --port 9876
   ```

2. Package the extension with the commands above.
3. In VS Code or Cursor, run `Extensions: Install from VSIX...` and choose the generated `.vsix`.
4. Run `Open Multi-Agent Panel` in VS Code or `Cursor: Open Multi-Agent Panel` in Cursor.

Marketplace 发布为可选流程；未配置 publisher token 时仅本地或 GitHub Release 分发，见 [PUBLISHING.md](./PUBLISHING.md)。
