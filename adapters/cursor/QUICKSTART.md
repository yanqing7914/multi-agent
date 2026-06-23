# Cursor Multi-Agent Quickstart

Dependency-free Python 3. Reuses OpenClaw mission-control scripts.

## 0. Install Native Skill

From the extracted Cursor package root:

```bash
python3 scripts/install_native_skills.py --client cursor --scope primary --force
python3 scripts/install_native_skills.py --client cursor --check
```

For a friendlier readiness report with Chinese remediation hints:

```bash
python3 scripts/doctor.py --client cursor
```

Reload Cursor. Then ask Cursor Agent:

```text
Use cursor-multi-agent. Split this into scoped task cards, run Workers through the local agent CLI bridge, collect result reports, then audit the diff.
```

### Install the Cursor CLI (required for automatic Workers)

The full Worker bridge runs Cursor's terminal agent. The binary is `agent` (the
legacy alias `cursor-agent` also works). If `complete_worker_bridge_ready=false`,
install it:

```bash
# macOS / Linux / WSL
curl https://cursor.com/install -fsS | bash

# Windows (native PowerShell)
irm 'https://cursor.com/install?win32=true' | iex
```

Reopen your shell and verify with `agent --version`. If the command is not found,
add `~/.local/bin` to your `PATH`. The bridge also needs `bash` + `tmux`; on
native Windows run the bridge from WSL. Without the CLI you can still use the
manual fallback in step 2b.

## 1. Generate Task Cards

From target repo root:

```bash
python3 /path/to/cursor-multi-agent/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/cursor-multi-agent/adapters/cursor/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

## 2a. Full Mode: Cursor CLI Bridge

Cursor 3's in-App Agents Window (`/multitask`) can also split a request into parallel subagents with their own worktrees and PRs; native integration with this adapter is on the roadmap, while the CLI bridge below stays the deterministic scripted/CI path.

Use this for automatic Workers from Cursor App or Cursor CLI:

```bash
python3 /path/to/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

For synchronous debugging:

```bash
python3 /path/to/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor \
  --foreground \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

## 2b. Manual Fallback

Use only when `agent` CLI is unavailable:

```bash
python3 /path/to/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Open or paste the returned `prompt_path` into Cursor Agent in the target workspace. The Agent must write both result reports before claiming completion.

## 3. Sync Gates And Audit

```bash
python3 /path/to/cursor-multi-agent/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync

git diff --name-only > .codex-multi-agent/changed-files.txt
python3 /path/to/cursor-multi-agent/adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

## Self-check

```bash
python3 /path/to/cursor-multi-agent/scripts/install_native_skills.py --client cursor --check
python3 /path/to/cursor-multi-agent/adapters/cursor/scripts/cursor_self_check.py
```
