# Codex App Native Acceptance

This checklist verifies the real Codex App native path, not only script self-checks.

## What This Proves

- Codex App can discover `multi-agent-worker` and `multi-agent-reviewer`.
- Main can spawn native subagents with scoped prompts.
- Subagents can write JSON + Markdown result reports.
- Main can wait for completion and close agents to free concurrency slots.
- On-disk evidence can be validated by `dogfood_codex_app.py`.

It does not prove OS-level path isolation. `allowed_paths`, `blocked_commands`,
and `may_use_skills` remain prompt-guided contracts plus audit checks.

## Smoke Directory

Use:

```text
.codex-multi-agent/session-smoke/
```

This directory is runtime state and must not be committed.

## Worker Smoke

Spawn a `multi-agent-worker` with:

```text
Allowed paths:
- .codex-multi-agent/session-smoke/**

Task:
Write .codex-multi-agent/session-smoke/worker-smoke.json and
.codex-multi-agent/session-smoke/worker-smoke.md.

JSON fields:
- task_id: SMOKE001
- role: Worker
- status: completed
- required_paths_verified: true
- files_changed: both files created
- files_read
- tools_used
- workspace_observed
```

After it completes, call `close_agent`.

## Reviewer Smoke

Spawn a `multi-agent-reviewer` with:

```text
Allowed paths:
- .codex-multi-agent/session-smoke/**

Task:
Read .codex-multi-agent/session-smoke/worker-smoke.json and
.codex-multi-agent/session-smoke/worker-smoke.md.
Write .codex-multi-agent/session-smoke/reviewer-smoke.json and
.codex-multi-agent/session-smoke/reviewer-smoke.md.

Reviewer must be read-only for project source files and must report:
- task_id: SMOKE002
- role: Reviewer
- status: completed
- required_paths_verified: true
- files_changed: []
- files_read: worker smoke files
- findings: []
```

After it completes, call `close_agent`.

## Validate Evidence

Run:

```bash
python3 adapters/codex/scripts/dogfood_codex_app.py \
  --session-smoke-state .codex-multi-agent/session-smoke

python3 adapters/codex/scripts/doctor_codex.py
```

Expected:

- dogfood validator returns `ok: true`.
- doctor shows `Session native smoke: OK`.

## Full Native Plan Check

Script-level plan/finalizer checks:

```bash
python3 adapters/codex/scripts/prepare_native_plan.py --self-check
python3 adapters/codex/scripts/finalize_native_run.py --self-check
```

These checks validate spawn-plan shape and finalization/audit behavior, but they
do not replace the real App smoke above.
