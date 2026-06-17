# Cursor Multi-Agent Quickstart

Dependency-free Python 3. Reuses OpenClaw mission-control scripts.

## 0. Install Cursor Rules

Copy or merge this package's rule file into the target workspace:

```text
.cursor/rules/multi-agent-coding.mdc
```

Then ask Cursor Agent explicitly:

```text
Use the multi-agent-coding workflow. Split this into scoped task cards, run one
Cursor Agent prompt per Worker/Reviewer, collect result reports, then audit the diff.
```

## 1. Generate Task Cards

From target repo root:

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/multi-agent-coding/adapters/cursor/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

## 2a. Cursor Desktop Prompt Path

Use this when the user is working inside Cursor Desktop:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime cursor-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Open or paste the returned `prompt_path` into Cursor Agent in the target
workspace. The Agent must write both result reports before claiming completion.

## 2b. Cursor CLI Worker Path

Use this for automatic tmux-backed workers:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Attach with the returned `tmux attach -t ...` command. For synchronous debugging:

```bash
python3 /path/to/multi-agent-coding/adapters/cursor/scripts/launch_cursor_worker.py \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --foreground
```

## 3. Sync Gates And Audit

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync

git diff --name-only > .codex-multi-agent/changed-files.txt
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

## Self-check

```bash
python3 /path/to/multi-agent-coding/adapters/cursor/scripts/cursor_self_check.py
python3 /path/to/multi-agent-coding/scripts/validate_all_adapters.py
```
