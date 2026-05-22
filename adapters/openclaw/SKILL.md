---
name: openclaw-multi-agent
description: OpenClaw/Her-specific multi-agent coding workflow for complex multi-role collaboration. Use when OpenClaw should coordinate sessions_spawn/sessions_send workers for research, scoped implementation, read-only review, SSRD/security review, verification, and diff audit. Do not use for simple coding, explicit single-agent coding-agent tasks, direct ACP routing handled by acp-router, or batch homogeneous jobs better handled by parallel-claude.
---

# openclaw-multi-agent

Use this OpenClaw-specific adapter for complex coding work that needs multiple roles, session handoffs, scoped Workers, read-only Reviewers, and main-session diff audit.

## Boundary With Local Skills

- Simple coding: do it directly in the main session.
- Explicit Claude/Codex/Gemini routing: use `acp-router`.
- Batch homogeneous jobs: use `parallel-claude`.
- Complex multi-role collaboration: use this skill.

## Trigger

Use this skill when the user asks for multi-agent coding, multiple OpenClaw sessions, parallel research, multiple reviewers, SSRD review, scoped implementation, complex refactor, or multi-module bug investigation.

Do not use it when a task is single-file, obvious, low-risk, or cannot be safely split by paths.

## Roles

- Main: plans, spawns sessions, sends task cards, collects reports, audits diffs, verifies, and delivers.
- Explorer: read-only session for code research and evidence.
- Worker: write-capable session limited to `allowed_paths`.
- Reviewer: read-only session for findings; may use `ssrd` if authorized.
- Verifier: test/build/repro session; read-only unless explicitly assigned.

## OpenClaw Session Flow

1. Decide whether this task needs multi-agent work.
2. Create task cards with `scripts/create_task_cards.py` or `templates/task-card.md`.
3. Spawn sessions with clear names, for example `explorer-backend`, `worker-ui`, `reviewer-security`.
4. Send each task card with `sessions_send`.
5. Require each session to return `templates/result-report.md` format and a completion signal.
6. Collect changed paths from Workers.
7. Run `scripts/audit_worker_output.py` against ownership and touched paths.
8. Main session performs diff audit and resolves conflicts.
9. Run Reviewer and Verifier sessions as needed.
10. Deliver final answer with changed files, validation, findings handled, and risks.

## Runtime Choice

Prefer the runtime that matches the requested agent:

- Use `runtime=acp` when routing to an ACP-backed coding agent.
- Use native OpenClaw subagent/session runtime when no external agent is required.
- Keep Reviewer sessions read-only regardless of runtime.

## Worker Rules

Workers must have `allowed_paths`, `blocked_paths`, `allowed_commands`, `blocked_commands`, and `stop_conditions`.

Workers must stop when they need to:

- edit outside `allowed_paths`
- read secrets or credentials
- install dependencies
- deploy, publish, push, reset, or mutate production data
- resolve unclear conflicts with user changes

Workers may use other skills only when `may_use_skills` explicitly lists them. Review skills such as `ssrd` belong to Reviewer sessions by default, not Worker sessions.

## Reviewer Rules

Reviewers are read-only. They do not modify files, run destructive commands, or spawn sessions. They report findings by severity with evidence and recommendations. If the user asks multiple agents to review something with `ssrd`, spawn multiple Reviewer sessions and set `may_use_skills: [ssrd]`.

## Audit Requirement

Before final delivery, the Main session must audit:

- Worker touched paths are within ownership.
- No blocked paths or secret files were touched.
- No two Workers modified the same file unless explicitly approved.
- Validation results exist or missing validation is explained.
- User pre-existing changes were not overwritten.

Use `scripts/audit_worker_output.py` when task cards or result files are available.

## Final Delivery

Return:

- what changed
- files touched
- validation run
- validation not run
- reviewer findings handled
- residual risks
- next options
