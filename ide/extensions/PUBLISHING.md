# IDE 扩展发布指南

本文说明如何将 `ide/extensions/vscode` 与 `ide/extensions/cursor` 发布到 VS Code Marketplace 与 OpenVSX。仓库内已准备好脚本与 `package.json` 字段，**不会**在 CI 中自动发布。

## 前置条件

1. **替换 publisher 占位符**  
   在两个 `package.json` 中将 `"publisher": "<PUBLISHER_TBD>"` 改为你注册的 publisher ID（两处必须一致）。

2. **扩展图标（可选但推荐）**  
   `package.json` 中 `icon` 指向 `images/icon.png`。该文件当前为占位路径，打包前请放入 128×128 PNG；若暂缺，vsce 可能警告，但不影响本地 `.vsix` 打包。

3. **Node.js**  
   需要可用的 `node` 与 `npm`（与本地构建相同）。

## 1. 注册 VS Code Marketplace Publisher

1. 打开 [Visual Studio Marketplace 管理页](https://marketplace.visualstudio.com/manage)。
2. 使用 Microsoft 账号登录，创建 **Publisher**（记下 Publisher ID，用于替换 `<PUBLISHER_TBD>`）。
3. 首次发布前可在网页上创建扩展条目，也可完全通过 `vsce publish` 创建。

## 2. 生成 Azure DevOps PAT（VSCE）

1. 打开 [Azure DevOps](https://dev.azure.com/) → User settings → **Personal access tokens**。
2. 新建 PAT，Scope 选择 **Marketplace** → **Manage**（发布扩展所需）。
3. 将 token 导出为环境变量（勿提交到 git）：

   ```bash
   export VSCE_PAT='你的 PAT'
   ```

## 3. 注册 OpenVSX Namespace 与 Token

1. 打开 [Open VSX](https://open-vsx.org/)，用 GitHub 等方式登录。
2. 在 [用户设置](https://open-vsx.org/user-settings/namespaces) 中创建与 publisher ID **一致** 的 namespace（需与 `package.json` 的 `publisher` 字段匹配）。
3. 生成 **Access Token**，导出为：

   ```bash
   export OVSX_PAT='你的 OpenVSX token'
   ```

Cursor 等基于 OpenVSX 的 IDE 通常从此 registry 拉取扩展。

## 4. 使用 publish.sh 发布

在仓库根目录执行：

```bash
# 仅打包（不发布）
EXTENSION=vscode ./ide/extensions/scripts/publish.sh

# 打包并发布到两个市场
EXTENSION=vscode VSCE_PAT="$VSCE_PAT" OVSX_PAT="$OVSX_PAT" ./ide/extensions/scripts/publish.sh

# Cursor 风味扩展
EXTENSION=cursor VSCE_PAT="$VSCE_PAT" OVSX_PAT="$OVSX_PAT" ./ide/extensions/scripts/publish.sh
```

脚本流程：`npm ci` → `npm run compile` → `vsce package` →（有 token 时）`vsce publish` / `ovsx publish`，最后打印 `.vsix` 绝对路径。

查看帮助：

```bash
./ide/extensions/scripts/publish.sh --help
```

## 5. 发布失败常见原因

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `Missing publisher name` / publisher 无效 | 仍为 `<PUBLISHER_TBD>` 或与 Marketplace 不一致 | 修改两个 `package.json` 的 `publisher` |
| `401` / `Access Denied`（vsce） | PAT 过期或 scope 不是 Marketplace Manage | 重新生成 PAT 并 `export VSCE_PAT` |
| `Extension version already exists` | 同版本已发布 | 在 `package.json` 中递增 `version` 后重试 |
| OpenVSX namespace 不匹配 | `publisher` 与 OpenVSX namespace 不一致 | 在 OpenVSX 创建同名 namespace |
| `ovsx` 命令找不到 | 未安装 CLI | 脚本使用 `npx ovsx`，需网络拉取；或 `npm i -g ovsx` |
| 图标 / README 警告 | `images/icon.png` 缺失 | 添加 128×128 PNG 或暂时忽略警告 |
| `npm ci` 失败 | `package-lock.json` 与 `package.json` 不同步 | 在对应扩展目录运行 `npm install` 并提交 lockfile |

## 6. 不走 Marketplace：GitHub Release 分发

若暂不注册 publisher，可将 `.vsix` 附在 GitHub Release 供用户手动安装：

```bash
EXTENSION=vscode ./ide/extensions/scripts/publish.sh
gh release upload v0.1.0 ide/extensions/vscode/*.vsix --repo yanqing7914/multi-agent
```

用户在 VS Code / Cursor 中执行 **Extensions: Install from VSIX...** 选择下载的文件即可。
