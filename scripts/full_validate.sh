#!/usr/bin/env bash
# Project-level smoke "everything" runner — continues on failure, exits non-zero if any step failed.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAILED=0

run_step() {
  local name="$1"
  shift
  if "$@"; then
    echo "[PASS] $name"
  else
    echo "[FAIL] $name" >&2
    FAILED=1
  fi
}

run_step "validate_all_adapters" python3 scripts/validate_all_adapters.py
run_step "validate_all_openclaw" python3 adapters/openclaw/scripts/validate_all.py
run_step "run_local_demo" python3 adapters/openclaw/scripts/run_local_demo.py --out /tmp/openclaw-demo-full-validate --keep
run_step "run_bench" python3 bench/run_bench.py --self-check --dry-runtime
run_step "swebench_lite" python3 bench/swebench-lite/run_swebench_lite.py --self-check
run_step "mcp_self_check" python3 mcp/self_check.py
run_step "ide_self_check" python3 ide/self_check.py
run_step "ide_extension_build_check" bash ide/extensions/scripts/build_check.sh
run_step "git_tool" python3 tools/git_tool.py --self-check
run_step "test_runner_tool" python3 tools/test_runner_tool.py --self-check
run_step "lint_tool" python3 tools/lint_tool.py --self-check
run_step "shell_tool" python3 tools/shell_tool.py --self-check
run_step "repo_index_tool" python3 tools/repo_index_tool.py --self-check
run_step "memory_log" python3 adapters/openclaw/scripts/memory_log.py --self-check
run_step "dogfood_claude" python3 adapters/claude-code/scripts/dogfood_claude.py --self-check
run_step "memory_rotate" python3 adapters/openclaw/scripts/memory_rotate.py --self-check
run_step "openclaw_worker_outcome" python3 adapters/openclaw/scripts/openclaw_worker_outcome.py --self-check

if [[ "$FAILED" -ne 0 ]]; then
  echo "full_validate: one or more steps failed" >&2
  exit 1
fi
echo "full_validate: all steps passed"
