# Codex Multi-Agent — Quickstart

Dependency-free Python 3. Reuses OpenClaw mission-control scripts.

## 1. Generate task cards

```bash
cd /path/to/target-repo
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/multi-agent-coding/adapters/codex/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

## 2. Validate bridge

```bash
python3 /path/to/multi-agent-coding/adapters/codex/scripts/codex_self_check.py
python3 /path/to/multi-agent-coding/scripts/validate_all_adapters.py
```

## 3. Launch a worker

Ensure Codex CLI is authenticated (user environment — not stored in repo).

```bash
export CODEX_SANDBOX=workspace-write   # default; use read-only only for Explorer-style tasks
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Overrides: `CODEX_MODEL`, `CODEX_BIN`, `CODEX_SANDBOX` (or `--model`, `--codex-bin`, `--sandbox` on the launcher).

## 4. Parallel workers

Use git worktrees — see [README.md](README.md).

## 5. Gates & audit

Follow [OpenClaw QUICKSTART](../openclaw/QUICKSTART.md) steps 5–7.
