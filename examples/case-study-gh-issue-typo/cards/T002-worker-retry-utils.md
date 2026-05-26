task_id: T002
session_name: worker-retry-utils
runtime: acp
mode: implement
role: Worker
title: Fix docstring typo (retrun → return)
objective: Apply docs-only fix per mock-issue.md; align after.py with corrected docstring
context: Explorer T001 confirms single typo in before.py line 12
workspace_root: <repo>/examples/case-study-gh-issue-typo
target_repo: <repo>
write_permission: true
allowed_paths:
  - examples/case-study-gh-issue-typo/**
required_paths:
  - examples/case-study-gh-issue-typo/before.py
blocked_paths:
  - .env
validation_required:
  - Produce result JSON and mock-pr.md narrative
result_report_json: .codex-multi-agent/results/T002-worker-retry-utils.json
result_report_markdown: .codex-multi-agent/results/T002-worker-retry-utils.md
