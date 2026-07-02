---
name: openclaw-multi-agent
description: OpenClaw/Her-specific multi-agent coding workflow for complex multi-role collaboration. Use when OpenClaw should coordinate sessions_spawn/sessions_send workers for research, scoped implementation, read-only review, SSRD/security review, verification, and diff audit. Do not use for simple coding, explicit single-agent coding-agent tasks, direct ACP routing handled by acp-router, or batch homogeneous jobs better handled by parallel-claude.
---

# openclaw-multi-agent

Use this OpenClaw-specific adapter for complex coding work that needs multiple roles, session handoffs, scoped Workers, read-only Reviewers, and main-session diff audit.

Install only this folder as a skill. You do not need the full root repo to run it.

## When To Use

Use when the task needs at least two of:

- parallel code research across modules
- scoped implementation with path ownership
- read-only review from multiple perspectives
- SSRD/security review via authorized Reviewer sessions
- verification after multi-module changes
- diff audit before final delivery

Typical triggers:

- user asks for multi-agent coding or multiple OpenClaw sessions
- feature spans backend + frontend + tests
- complex bug needs Explorer then Worker then Verifier
- user asks multiple agents to review with `ssrd`

## When Not To Use

Stop and use a simpler path when:

- the change is single-file or low-risk
- the user explicitly wants one coding agent via `acp-router`
- the job is a batch of similar homogeneous tasks via `parallel-claude`
- ownership cannot be expressed with clear `allowed_paths`
- the task only needs explanation, docs, or a tiny fix in main session

## Boundary With Local Skills

| Situation | Use |
| --- | --- |
| Simple coding in one session | main session directly |
| Explicit Claude/Codex/Gemini routing | `acp-router` |
| Batch homogeneous jobs | `parallel-claude` |
| Complex multi-role collaboration | this skill |

## Roles

- Main: plans, creates task cards, spawns sessions, sends cards, collects reports, audits diffs, verifies, delivers.
- Explorer: read-only research and evidence.
- Worker: write-capable, limited to `allowed_paths`.
- Reviewer: read-only findings; may use `ssrd` when authorized.
- Verifier: test/build/repro; read-only unless explicitly assigned as Worker.

## OpenClaw Tool Mapping

Map roles to OpenClaw session tools like this:

| Role | Spawn | Send | Yield |
| --- | --- | --- | --- |
| Main | optional helper sessions only when needed | sends each task card | waits while Workers/Reviewers run |
| Explorer | `sessions_spawn name="explorer-<scope>" runtime="<runtime>"` | `sessions_send session="explorer-<scope>" message="<task card>"` | `sessions_yield session="explorer-<scope>"` until result report arrives |
| Worker | `sessions_spawn name="worker-<scope>" runtime="<runtime>"` | `sessions_send session="worker-<scope>" message="<task card>"` | `sessions_yield session="worker-<scope>"` until JSON/Markdown report arrives |
| Reviewer | `sessions_spawn name="reviewer-<focus>" runtime="<runtime>"` | `sessions_send session="reviewer-<focus>" message="<task card>"` | `sessions_yield session="reviewer-<focus>"` until findings report arrives |
| Verifier | `sessions_spawn name="verifier" runtime="<runtime>"` | `sessions_send session="verifier" message="<task card>"` | `sessions_yield session="verifier"` until validation report arrives |

Rules:

- Only Main spawns coordination sessions by default.
- Workers and Reviewers must not spawn other sessions unless a task card explicitly sets `may_spawn_sessions: true`.
- Use `sessions_yield` whenever Main is waiting on a child session result instead of polling manually.
- Put the full task card in the `sessions_send` message, including `allowed_paths`, `blocked_paths`, and `result_report_paths`.

## Runtime Choice: ACP vs Subagent

Choose runtime before spawning:

| Runtime | Use when |
| --- | --- |
| `acp` | the child session should run through an ACP-backed coding agent such as Claude Code, Codex, or Gemini |
| `subagent` or `native` | OpenClaw's own session/subagent runtime is enough and no external ACP agent is requested |

Guidance:

- Prefer `runtime=acp` when the user names a specific external coding agent.
- Prefer `runtime=subagent` for read-only Explorers/Reviewers or repo-local work that does not need ACP.
- Keep Reviewer sessions read-only regardless of runtime.
- Do not assign `ssrd` or other review skills to Worker sessions by default.

## Worker vs Reviewer Boundaries

Workers:

- may edit only inside `allowed_paths`
- `files_changed` must list only business code — never list your own result report files under `.codex-multi-agent/results/`
- must leave `files_changed` empty in reports only if they made no edits
- must stop on scope expansion, secrets, dependency install, deploy/push, or user-change conflicts
- may use other skills only when listed in `may_use_skills`

Reviewers:

- never edit files
- never report non-empty `files_changed`
- never spawn sessions
- may use review skills such as `ssrd` only when authorized in the task card
- report findings by severity with evidence and recommendations

If the user asks "have multiple agents review this with ssrd", create Reviewer sessions, not Workers.

## OpenClaw Session Flow

1. Decide whether multi-agent work is justified.
2. Create mission-control state under `.codex-multi-agent/` locally; do not commit it unless the user asks.
3. Generate task cards, ownership, status, and run plan:

```bash
python adapters/openclaw/scripts/create_task_cards.py \
  --task "Add vehicle favorite feature" \
  --mode implement \
  --modules backend frontend tests \
  --out .codex-multi-agent
```

Or from the bundled example:

```bash
python adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml adapters/openclaw/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

3b. **Workspace rule:** Every task card includes absolute `workspace_root` / `target_repo`. Child sessions must `cd` there first and run `preflight_command`. OpenClaw may ignore `sessions_spawn` cwd — never assume the child started in the target repo.

4. Before each spawn wave, sync gates:

```bash
python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync
```

5. Spawn sessions with stable names such as `explorer-backend`, `worker-ui`, `reviewer-security`, `verifier`.
6. Send each task card with `sessions_send`. Each card lists explicit `main_commands` and `gate` requirements.
7. Require each session to write both result files listed in `result_report_paths`:
   - JSON for machine audit
   - Markdown for human review
   - Include preflight fields: `workspace_observed`, `required_paths_checked`, `required_paths_missing`, `required_paths_verified`, `files_read`
8. Use `sessions_yield` while waiting for completion signals.
9. Mark tasks complete and resync:

```bash
python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --task-id T002 --status completed
python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync
```

10. Collect Worker changed paths from result reports and/or:

```bash
python3 adapters/openclaw/scripts/capture_changed_files.py --state-dir .codex-multi-agent  # staged + unstaged + untracked
```

11. Audit scope and write audit JSON:

```bash
python adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit \
  --state-dir .codex-multi-agent
```

12. Summarize for final delivery:

```bash
python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --summarize
```

13. Main performs diff audit, resolves conflicts, confirms all gates in `status.json`, and delivers.

## Anti-False-Completion Rule (Hard)

A subagent in the wrong workspace must **not** pass a gate by reporting `status=completed` without reading the requested files.

Generated task cards include `required_paths` and a mandatory preflight step. Module `openclaw_adapter` maps to `adapters/openclaw/**`.

Result reports must include `workspace_observed`, `required_paths_checked`, `required_paths_missing`, `required_paths_verified`, and `files_read`.

`update_task_status.py --sync` downgrades `status=completed` to `blocked` when `required_paths_verified=false`, `required_paths_missing` is non-empty, or **thin evidence** (empty `files_read` on Reviewer/Explorer/Verifier with concrete `required_paths`). **Verifier:** list every file inspected in `files_read` — pytest passing alone is not evidence. Gates fail until the task reruns from the correct workspace or reports `status=blocked` honestly.

For repos where code lives under `src/**` rather than `{module}/**`, pass explicit module paths in YAML/JSON (`modules: [{name: fizzbuzz, paths: [src/**, tests/**]}]`) or use `--from-json`.

Validate locally without spawning agents: `python3 adapters/openclaw/scripts/validate_all.py`

## Bundled Files

Load only what you need:

- `QUICKSTART.md`: fresh-checkout install and validation
- `README.md`: install, Golden Path, workspace workaround
- `scripts/create_task_cards.py`: generate task cards, ownership, status, run plan
- `scripts/update_task_status.py`: sync gates, update task status, summarize run
- `scripts/audit_worker_output.py`: scope audit for Worker outputs
- `scripts/verify_workspace.py`: preflight path checks for subagents
- `scripts/run_local_demo.py`: deterministic demo and combined self-check
- `scripts/validate_all.py`: run all script self-checks in one command
- `templates/task-card.md`: manual task-card template
- `templates/result-report.md`: result report template
- `templates/ownership.example.json`: ownership schema example
- `examples/favorite-feature.yaml`: sample multi-module task definition

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

Before final delivery, Main must audit:

- Worker touched paths are within ownership
- no blocked paths or secret files were touched
- no two Workers modified the same file unless explicitly approved
- every Worker submitted a result report
- validation results exist or missing validation is explained
- user pre-existing changes were not overwritten

Use `scripts/audit_worker_output.py` whenever task cards or result files exist. Add `--strict` if missing Worker reports or unowned global changes should fail the audit. Use `--write-audit --state-dir .codex-multi-agent` to persist audit JSON for gate tracking.

**Audit contract:** treat `"ok": true` as scope_audit **passed** only when `gate.status=passed` (exit 0). Warnings ⇒ `ok=false`, gate `pending`, exit `2`. After any `changed-files.txt` update, rerun audit with `--write-audit` so digest metadata stays current; `update_task_status.py --sync` marks stale audits as `pending`.

Check `status.json` gates before final delivery. Run `update_task_status.py --summarize` to produce a Main-facing run summary.

## Final Delivery

Return:

- what changed
- files touched
- validation run
- validation not run
- reviewer findings handled
- residual risks
- next options

Use `templates/result-report.md` for child session output and summarize in the main session response.
