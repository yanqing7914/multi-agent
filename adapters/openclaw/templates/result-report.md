task_id:
session_name:
role:
status: completed | blocked | failed

summary:

workspace_observed:
required_paths_checked: []
required_paths_missing: []
required_paths_verified: true | false
files_read: []
tools_used: []
files_changed: []
skills_used: []
commands_run: []
validation:
  - command:
    result: passed | failed | not_run
    notes:
findings: []
risks: []
blockers: []
handoff_notes:

# Notes

- **Preflight is mandatory.** Run `pwd`, confirm each task-card `required_paths` entry exists and is readable before any review or edit work.
- Set `status=completed` only when `required_paths_verified=true` and `required_paths_missing` is empty.
- List every file you actually opened in `files_read`. Empty `files_read` with concrete `required_paths` and `required_paths_verified=true` is treated as thin evidence and will block gates.
- List every framework tool you invoked in `tools_used` (e.g. `git_tool`, `test_runner_tool`, `repo_index_tool`). Undeclared tool references in result reports produce audit warnings.
- If required paths are missing, set `status=blocked`, `required_paths_verified=false`, list missing paths, and do not pretend to review or edit files you could not read.
- Workers must list every edited path in `files_changed`.
- Reviewers and Explorers should keep `files_changed: []`.
- Also write a companion JSON file at the path listed in the task card's `result_report_paths.json`.
- Reviewers: list findings with severity in JSON; they are aggregated into `.codex-multi-agent/findings/review-findings.json` when Main runs `update_task_status.py --sync`.
- Minimum JSON fields for audit:

```json
{
  "task_id": "T002",
  "session_name": "worker-backend",
  "role": "Worker",
  "status": "completed",
  "workspace_observed": "/path/to/repo",
  "required_paths_checked": ["backend/**"],
  "required_paths_missing": [],
  "required_paths_verified": true,
  "files_read": ["backend/src/example.py"],
  "tools_used": ["repo_index_tool", "git_tool"],
  "files_changed": ["backend/src/example.py"]
}
```

completion_signal: "<task_complete task_id='T___' status='completed'>"
