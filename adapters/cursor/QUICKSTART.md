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
Use cursor-multi-agent. Split this into scoped task cards, then for each card spawn a Cursor subagent (Worker limited to allowed_paths; Reviewer read-only) to do the work and write JSON + Markdown reports. Collect reports, then audit the diff.
```

In Cursor App the primary path is **in-App subagent delegation**: the Main agent
spawns a Cursor subagent per Worker/Reviewer. No external CLI is required.

### (Optional) Install the Cursor CLI — only for the scripted bridge

You only need the `agent` CLI if you want the scripted/CI bridge in step 2b
(`run_multi_agent.py --runtime cursor`). The binary is `agent` (legacy alias
`cursor-agent` also works):

```bash
# macOS / Linux / WSL
curl https://cursor.com/install -fsS | bash

# Windows (native PowerShell)
irm 'https://cursor.com/install?win32=true' | iex
```

Reopen your shell and verify with `agent --version`. If not found, add
`~/.local/bin` to your `PATH`. The bridge also needs `bash` + `tmux`; on native
Windows run it from WSL.

## 1. Generate Task Cards

From target repo root:

```bash
python3 /path/to/cursor-multi-agent/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/cursor-multi-agent/adapters/cursor/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

## 2. Dispatch Workers — In-App Subagent Delegation (primary)

In Cursor App, the Main agent dispatches each Worker/Reviewer by **spawning a
Cursor subagent** with the task-card body + role + `allowed_paths` + the two
`result_report_paths`. Worker edits only within `allowed_paths`;
Reviewer/Explorer/Verifier stay read-only. Collect each subagent's JSON +
Markdown report, then go to step 3 (audit). No external CLI is needed. If your
Cursor agent cannot delegate, use `/multitask` (type it in Cursor 3) or the
optional bridge in 2a.

## 2a. (Optional) Scripted Mode: Cursor CLI Bridge

For shell/CI-driven Workers (needs the `agent` CLI + tmux; WSL on native Windows):

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

Use only when neither delegation nor the `agent` CLI is available:

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
