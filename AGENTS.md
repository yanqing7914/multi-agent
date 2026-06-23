# AGENTS.md — Repo-wide multi-agent conventions

This file documents how Workers, Reviewers, Verifiers, and Main should behave in this repository.

## Roles

| Role | Write? | Must produce |
| --- | --- | --- |
| Explorer | No | Evidence in `files_read`; no `files_changed` |
| Worker | Yes (scoped) | `files_changed`, result JSON + Markdown |
| Reviewer | No | Findings with severity; `files_read` |
| Verifier | No | `commands_run`, `validation`, `files_read` |

## Required result-report fields

- `workspace_observed` — output of `pwd` after `cd` to `workspace_root`
- `required_paths_verified` — `true` only when required paths were readable
- `files_read` — every file opened (empty + verified=true → **thin_evidence** blocked)
- `tools_used` — every framework tool invoked (e.g. `git_tool`, `test_runner_tool`); undeclared tools → audit **warning**

## Safety gates (do not bypass)

- `false_completion` — completed without verified required paths
- `thin_evidence` — verification claimed without `files_read`
- `workspace_mismatch` — `workspace_observed` ≠ target repo
- `stale_audit` — changed-files digest out of date
- `missing_result_report_json` — JSON companion missing
- `invalid_status_token` — status not in allowed set
- `mission_control_exempt` — do not list `.codex-multi-agent/results/*` in Worker `files_changed`

## Tools layer

Use stdlib wrappers under `tools/` (dependency-free):

```bash
python3 tools/git_tool.py --help
python3 tools/test_runner_tool.py --help
python3 tools/lint_tool.py --help
python3 tools/shell_tool.py --help
python3 tools/repo_index_tool.py --help
python3 tools/worktree_tool.py --help   # one git worktree+branch per Worker (physical isolation)
```

Each tool accepts JSON-in/JSON-out via stdin or `--json-in`, supports `--help`, and ships a `--self-check`.

`worktree_tool.py` gives parallel Workers physical isolation on top of the
logical `allowed_paths` split: plan one worktree+branch per write-permission
Worker straight from `ownership.json` so concurrent edits never overwrite each
other (default location is a `<repo>.worktrees/` sibling, to keep the main tree's
`git status` clean for scope audits).

```bash
python3 tools/worktree_tool.py --action plan --ownership .codex-multi-agent/ownership.json   # add --create to make them
```

## Dependency auto-unblock

`create_task_cards.py` persists the static dependency graph onto each
`ownership.json` task (`dependencies`). `update_task_status.py --sync` then
derives, per task in `status.json`: `dependencies`, `blocked_by` (prerequisites
not yet `completed`), and `ready_to_spawn` (pending AND unblocked). This is
advisory — it never changes gate pass/fail — and lets Main / loops pick the next
unblocked task. Query it directly:

```bash
python3 adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --ready
# -> {"ready": ["T001"], "blocked": {"T002": ["T001"], ...}}
```

The run summary also annotates each task with `[ready_to_spawn]` / `[blocked_by: …]`.

## Orchestration & ops scripts

Dependency-free (stdlib only); each ships a `--self-check` run by
`scripts/validate_all_adapters.py`.

| Script | Purpose |
| --- | --- |
| `scripts/install_native_skills.py` | Install native skills for `codex` / `cursor` / `claude` / `hermes` (`--client`, `--scope`, `--check`) |
| `scripts/run_multi_agent.py` | Cross-adapter Worker launcher; `--runtime` incl. `openclaw`, `hermes`, `codex(-native/-desktop)`, `cursor(-desktop)`, `claude-(code/desktop)` |
| `adapters/openclaw/scripts/run_loop.py` | Verifier-gated self-correction loop: maker = `run_multi_agent.py`, independent verifier = `--verify-command` (+ `--with-audit`), `maker != checker`, bounded by `--max-iterations`/budget |
| `adapters/openclaw/scripts/run_graph.py` | Dependency-ordered scheduler: repeatedly dispatch `ready_to_spawn` tasks via `run_multi_agent.py` until the graph completes / deadlocks; bounded by `--max-rounds`. Dry plan by default; `--execute` to launch |
| `scripts/doctor.py` | Readiness report for Codex/Cursor/Claude/Hermes with Chinese 下一步 hints (`--json`, `--self-check`) |
| `scripts/configure_mcp.py` | One-step MCP coordinator registration (Cursor/Claude JSON merge, Codex TOML print, Hermes YAML print); default dry-run, `--write` to persist |

## Adapters

Client adapters stay thin and reuse `adapters/openclaw/scripts/*` for cards,
gates, audits, and memory — they never duplicate gate logic.

- `adapters/openclaw/` — canonical mission-control reference implementation.
- `adapters/codex/`, `adapters/cursor/`, `adapters/claude-code/` — native skills + bridges/subagents.
- `adapters/cursor/` also has native orchestration paths: `scripts/prepare_cursor_sdk.py`, `sdk/`, `SDK.md` (headless `agent -p` and `@cursor/sdk`).
- `adapters/hermes/` — agentskills.io native skill that drives Workers via Hermes's native MCP client (`~/.hermes/config.yaml` `mcp_servers`) over the shared OpenClaw core.

## MCP coordinator

`mcp/multi-agent-coordinator/` exposes the mission-control core as MCP tools
(stdio, stdlib-only) so Cursor/Claude/Codex/Hermes can drive it natively:
`create_task`, `list_tasks`, `get_task`, `update_task_status`, `record_result`,
`check_path_allowed`, `record_touched_paths`, `request_skill_use`,
`approve_skill_use`, `record_finding`, `summarize_review`, `audit_scope`,
`generate_final_report`, `plan_worktrees` (git worktree isolation), and
`check_readiness` (doctor). Register it with `scripts/configure_mcp.py`; task
readiness (`ready_to_spawn`/`blocked_by`) is reachable via the
`multi-agent://state` resource.

## Memory

After each run, Main runs `update_task_status.py --summarize`, which appends a one-liner to `MEMORY.md`. Workers receive the latest memory tail in task card `context`.

## Example Worker checklist

1. `cd` to absolute `workspace_root`; run preflight.
2. Use declared `tools_used` only within `allowed_paths`.
3. Write JSON + Markdown result reports before completion signal.
4. Never install dependencies, push git, or touch secrets unless explicitly approved.
