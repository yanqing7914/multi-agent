#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

if ! command -v node >/dev/null 2>&1; then
  echo "extension build_check: skipping; node is not installed"
  exit 0
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "extension build_check: skipping; npm is not installed"
  exit 0
fi

for extension in vscode cursor; do
  dir="$ROOT/ide/extensions/$extension"
  echo "extension build_check: checking $extension"
  (cd "$dir" && npm install && npm run compile && npx --no-install vsce package --no-dependencies)
done
