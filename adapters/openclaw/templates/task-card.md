task_id: T___
session_name:
runtime: acp | subagent | native
mode: research | implement | fix | review | refactor
role: Explorer | Worker | Reviewer | Verifier
title:
objective:
context:
tools_used: []
workspace_root:
target_repo:
workspace_note: OpenClaw may ignore sessions_spawn cwd — child MUST cd to workspace_root (absolute) before reading files.
dependencies: []
preflight_command:
  - 'cd "<workspace_root>"'
  - pwd
  - python adapters/openclaw/scripts/verify_workspace.py --workspace-root "<workspace_root>" --required-paths "<path>"
write_permission: false
allowed_paths: []
required_paths: []
blocked_paths:
  - .env
  - .env.*
  - .npmrc
  - .pypirc
  - .netrc
  - ~/.ssh/**
  - ~/.codex/auth.json
  - '**/*.pem'
  - '**/*.key'
allowed_commands:
  - rg
blocked_commands:
  - npm install
  - pnpm install
  - git push
  - git reset --hard
  - deploy
  - publish
may_use_skills: []
may_spawn_sessions: false
validation_required: []
execution_guidance:
  - 'Preflight (required first step): run pwd; confirm each required_paths entry exists and is readable. If any required path is missing, set status=blocked, set required_paths_verified=false, list missing paths in required_paths_missing and handoff_notes, keep files_changed empty, and do not pretend to review or edit files you could not read.'
  - 'Record workspace_observed and list every file you actually opened in files_read. Do not set required_paths_verified=true with an empty files_read when required_paths lists concrete directories (thin_evidence will downgrade to blocked).'
  - 'List every framework tool invoked in tools_used (mirrors files_read). Task cards declare allowed tools_used; undeclared tool references in result reports produce audit warnings.'
  - 'Worker: files_changed must list only business code you edited — do NOT list your own result report files under .codex-multi-agent/results/.'
  - 'Verifier: run allowed validation commands; list every file you opened or inspected in files_read — pytest or test pass alone is not evidence.'
  - Follow role boundaries exactly; stop instead of expanding scope.
  - Write both result report files before sending completion_signal.
stop_conditions:
  - Need to edit outside allowed_paths
  - Required paths missing in workspace (set status=blocked; do not fake completion)
  - Need secret or credential access
  - Need dependency installation
  - Need deployment or production mutation
  - User changes may be overwritten
gate:
  id: explorers_complete | workers_complete | review_complete | verify_complete
  unblocks: next role phase
  pass_when:
    - result_report_paths.json exists
    - status is completed only after required_paths were visible/readable (required_paths_verified=true)
    - status is blocked with handoff_notes when required paths were missing
result_report_paths:
  json: .codex-multi-agent/results/T___-<session_name>.json
  markdown: .codex-multi-agent/results/T___-<session_name>.md
main_commands:
  before_spawn:
    - python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync
  spawn:
    - sessions_spawn name="<session_name>" runtime="<runtime>"
  send:
    - sessions_send session="<session_name>" message="<paste this task card>"
  yield:
    - sessions_yield session="<session_name>" when="waiting for result report"
  after_result:
    - python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --task-id T___ --status completed
    - python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync
openclaw_handoff:
  spawn: sessions_spawn name="<session_name>" runtime="<runtime>"
  send: sessions_send session="<session_name>" message="<paste this task card>"
  yield: sessions_yield session="<session_name>" when="waiting for result report"
completion_signal: "<task_complete task_id='T___' status='completed'>"
output_format: result-report.md + companion JSON
