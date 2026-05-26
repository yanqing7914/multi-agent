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
```

Each tool accepts JSON-in/JSON-out via stdin or `--json-in`.

## Memory

After each run, Main runs `update_task_status.py --summarize`, which appends a one-liner to `MEMORY.md`. Workers receive the latest memory tail in task card `context`.

## Example Worker checklist

1. `cd` to absolute `workspace_root`; run preflight.
2. Use declared `tools_used` only within `allowed_paths`.
3. Write JSON + Markdown result reports before completion signal.
4. Never install dependencies, push git, or touch secrets unless explicitly approved.
