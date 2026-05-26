#!/usr/bin/env bash
# Dependency-free CI smoke suite for non-GitHub environments.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
python3 -V
python3 scripts/validate_all_adapters.py
python3 adapters/openclaw/scripts/validate_all.py
python3 adapters/openclaw/scripts/run_local_demo.py --out /tmp/openclaw-demo-ci --keep
python3 bench/run_bench.py --self-check --dry-runtime
python3 mcp/multi-agent-coordinator/scripts/self_check.py
python3 ide/multi-agent-panel/scripts/self_check.py
python3 tools/git_tool.py --self-check
python3 tools/test_runner_tool.py --self-check
python3 tools/lint_tool.py --self-check
python3 tools/shell_tool.py --self-check
python3 tools/repo_index_tool.py --self-check
