task_id: T003
session_name: reviewer-docs
runtime: subagent
mode: review
role: Reviewer
title: Review docs-only typo fix
objective: Confirm Worker changed only the docstring; no behavior drift
context: Read before.py, after.py, and T002 result report
workspace_root: <repo>/examples/case-study-gh-issue-typo
target_repo: <repo>
write_permission: false
allowed_paths:
  - examples/case-study-gh-issue-typo/**
required_paths:
  - examples/case-study-gh-issue-typo/before.py
  - examples/case-study-gh-issue-typo/after.py
  - examples/case-study-gh-issue-typo/mock-pr.md
blocked_paths:
  - .env
validation_required:
  - findings list (empty if clean)
result_report_json: .codex-multi-agent/results/T003-reviewer-docs.json
result_report_markdown: .codex-multi-agent/results/T003-reviewer-docs.md
