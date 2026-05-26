task_id: T100
session_name: worker-app
runtime: acp
mode: implement
role: Worker
title: Add /ping endpoint to flask-cli demo
objective: |
  Add a new /ping HTTP route returning JSON {"pong": true} to the stdlib Flask-shaped demo,
  together with a `ping_payload()` helper in app/routes.py and a pytest assertion in
  tests/test_routes.py. This task was selected by the Claude Code (ACP) worker because
  T002 (/version) is already implemented in main, and the case study needs an actual diff
  to prove the adapter contract end-to-end without consuming Anthropic API quota.
context: |
  Hand-authored card for the real Claude Code (ACP) dogfood run captured under
  .runs/claude-code-real-20260526T020911Z/. Mirrors T002-worker-app.md scope and
  guardrails, but with a smaller and non-redundant change so the worker actually
  exercises files_changed > 0.
workspace_root: /mnt/c/Users/gongchenhao/Documents/Codex/2026-05-18/new-chat-3/multi-agent-coding/examples/case-study-flask-cli
target_repo: /mnt/c/Users/gongchenhao/Documents/Codex/2026-05-18/new-chat-3/multi-agent-coding/examples/case-study-flask-cli
write_permission: true
allowed_paths:
  - app/**
  - tests/**
required_paths:
  - app/**
  - tests/**
blocked_paths:
  - .env
  - .env.*
  - .npmrc
  - .pypirc
  - .netrc
  - ~/.ssh/**
  - **/*.pem
  - **/*.key
allowed_commands:
  - pytest
  - rg
blocked_commands:
  - npm install
  - pnpm install
  - git push
  - git reset --hard
validation_required:
  - PYTHONPATH=. pytest tests -q
result_report_paths:
  json: .runs/claude-code-real-20260526T020911Z/results/T100-worker-app.json
  markdown: .runs/claude-code-real-20260526T020911Z/results/T100-worker-app.md
completion_signal: "<task_complete task_id='T100' status='completed'>"
