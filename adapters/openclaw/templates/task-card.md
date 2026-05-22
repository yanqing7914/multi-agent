task_id: T___
session_name:
runtime: acp | subagent | native
mode: research | implement | fix | review | refactor
role: Explorer | Worker | Reviewer | Verifier
title:
objective:
context:
dependencies: []
allowed_paths: []
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
stop_conditions:
  - Need to edit outside allowed_paths
  - Need secret or credential access
  - Need dependency installation
  - Need deployment or production mutation
  - User changes may be overwritten
completion_signal: "<task_complete task_id='T___' status='completed'>"
output_format: result-report.md
