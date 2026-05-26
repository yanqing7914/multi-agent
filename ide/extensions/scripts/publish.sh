#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
EXTENSION="${EXTENSION:-vscode}"

usage() {
  cat <<'EOF'
用法: publish.sh [选项]

打包并（可选）发布 IDE 扩展到 VS Code Marketplace 与 OpenVSX。

环境变量:
  EXTENSION   扩展目录名: vscode | cursor（默认: vscode）
  VSCE_PAT    Azure DevOps PAT（Marketplace > Manage），设置后执行 vsce publish
  OVSX_PAT    OpenVSX 访问令牌，设置后执行 ovsx publish

示例:
  EXTENSION=vscode ./ide/extensions/scripts/publish.sh
  EXTENSION=cursor VSCE_PAT=xxx OVSX_PAT=yyy ./ide/extensions/scripts/publish.sh

详见: ide/extensions/PUBLISHING.md
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

case "$EXTENSION" in
  vscode|cursor) ;;
  *)
    echo "publish.sh: EXTENSION 必须是 vscode 或 cursor，当前: $EXTENSION" >&2
    exit 1
    ;;
esac

EXT_DIR="$ROOT/ide/extensions/$EXTENSION"
cd "$EXT_DIR"

echo "publish.sh: 进入 $EXT_DIR"
npm ci
npm run compile
npx vsce package --no-dependencies

VSIX_PATH="$(ls -1t ./*.vsix 2>/dev/null | head -n1 || true)"
if [[ -z "$VSIX_PATH" ]]; then
  echo "publish.sh: 未找到 .vsix 文件" >&2
  exit 1
fi

if [[ -n "${VSCE_PAT:-}" ]]; then
  echo "publish.sh: 发布到 VS Code Marketplace..."
  npx vsce publish --pat "$VSCE_PAT"
else
  echo "publish.sh: 跳过 VS Code Marketplace（未设置 VSCE_PAT）"
  echo "  设置 VSCE_PAT 后重新运行以发布，见 ide/extensions/PUBLISHING.md"
fi

if [[ -n "${OVSX_PAT:-}" ]]; then
  echo "publish.sh: 发布到 OpenVSX..."
  npx ovsx publish "$VSIX_PATH" -p "$OVSX_PAT"
else
  echo "publish.sh: 跳过 OpenVSX（未设置 OVSX_PAT）"
  echo "  设置 OVSX_PAT 后重新运行以发布，见 ide/extensions/PUBLISHING.md"
fi

echo "publish.sh: 打包完成 → $(realpath "$VSIX_PATH")"
