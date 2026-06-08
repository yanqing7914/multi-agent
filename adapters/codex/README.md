# Codex Multi-Agent Adapter

Thin Codex layer over [`adapters/openclaw/`](../openclaw/) mission-control scripts.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## Install

1. Install `codex-multi-agent-skill-*.zip` into the Codex skills directory.
2. Generate `.codex-multi-agent/` with `create_task_cards.py`.
3. Choose Desktop handoff (no Codex CLI) or CLI auto-run (`codex exec`).

## Usage: Codex Desktop App

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

This writes `.codex-multi-agent/desktop-workers/*.prompt.md`. Open each prompt in a new Codex Desktop session or task. The Worker writes the JSON/Markdown reports listed in the prompt; Main then runs sync and audit.

Expected output:

```json
{
  "ok": true,
  "runtime": "codex-desktop",
  "mode": "desktop-handoff",
  "prompt_path": ".../.codex-multi-agent/desktop-workers/T002-worker-backend.prompt.md",
  "result_json": ".../.codex-multi-agent/results/T002-worker-backend.json",
  "result_markdown": ".../.codex-multi-agent/results/T002-worker-backend.md"
}
```

## Usage: Codex CLI

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Direct CLI launcher:

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

- Codex Desktop handoff prompts for users without Codex CLI
- Preflight gate before `codex exec`
- Same result-report contract as OpenClaw v1
- OpenClaw gate sync / audit when Main runs shared scripts
- Worktree guidance for parallel Workers (docs only)

## Limitations

- Does not manage Codex auth or worktree lifecycle automatically.
- Desktop handoff does not automatically create a second Desktop session; Main/user opens the generated prompt in a new task.
- `codex exec` flags may vary by CLI version — override with `CODEX_BIN` if needed.
- Requires **result JSON file on disk** after run (not log extraction alone).
- CLI mode requires Codex CLI; Desktop handoff does not.
