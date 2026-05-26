# Codex Multi-Agent Adapter

Thin Codex layer over [`adapters/openclaw/`](../openclaw/) mission-control scripts.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## Install

1. Install this repo as a Codex skill (root `SKILL.md` + `adapters/codex/SKILL.md`).
2. Ensure **`codex`** CLI is installed and authenticated (user-managed; no API keys in scripts).
3. Generate `.codex-multi-agent/` with `create_task_cards.py`.

## Usage

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Direct launcher:

```bash
/path/to/multi-agent-coding/adapters/codex/scripts/launch_codex_worker.sh \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Optional env / CLI overrides:

| Variable / flag | Default | Purpose |
| --- | --- | --- |
| `CODEX_MODEL` / `--model` | `gpt-5.3-codex` | Model passed to `codex exec` |
| `CODEX_BIN` / `--codex-bin` | `codex` | Codex CLI binary |
| `CODEX_SANDBOX` / `--sandbox` | `workspace-write` | Sandbox mode (`read-only`, `workspace-write`, `danger-full-access`) |

```bash
export CODEX_MODEL=gpt-5.3-codex
export CODEX_BIN=codex
export CODEX_SANDBOX=workspace-write   # required for Workers that write files
```

The launcher always passes `--skip-git-repo-check` and defaults to `workspace-write` so read-only sandboxes do not silently block writes.

### Expected output (success)

```json
{
  "ok": true,
  "runtime": "codex",
  "model": "gpt-5.3-codex",
  "sandbox": "workspace-write",
  "workspace_root": "/path/to/target-repo",
  "result_markdown": ".../.codex-multi-agent/results/T002-worker-backend.md",
  "result_json_exists": true,
  "json_extracted": true
}
```

On failure (CLI error, read-only sandbox, missing JSON, quota patterns in log), the launcher prints `"ok": false`, an `"error"` reason, and exits non-zero. Pipelines use bash `pipefail` so `tee` does not mask Codex exit codes.

### Multi-worker / worktrees

Run one Codex exec per worktree to avoid file conflicts:

```bash
git worktree add ../wt-backend -b worker/backend
cd ../wt-backend
python3 .../create_task_cards.py --workspace-root "$(pwd)" --out .codex-multi-agent ...
launch_codex_worker.sh --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

## Self-check

```bash
python3 adapters/codex/scripts/codex_self_check.py
```

## What works today

- Preflight gate before `codex exec`
- Same result-report contract as OpenClaw v1
- OpenClaw gate sync / audit when Main runs shared scripts
- Worktree guidance for parallel Workers (docs only)

## Limitations

- Does not manage Codex auth or worktree lifecycle automatically.
- `codex exec` flags may vary by CLI version — override with `CODEX_BIN` if needed.
- Requires **result JSON file on disk** after run (not log extraction alone).
- No native Codex subagent orchestration beyond prompt-guided Main.
