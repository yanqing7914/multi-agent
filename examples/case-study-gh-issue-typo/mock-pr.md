# Fix docstring typo in `parse_retry_after` (closes #1842)

## Summary

Fixes the docstring typo reported in #1842: *"retrun"* → *"return"* when the `Retry-After` header is absent.

## Changes

- `retry_utils.py`: one-word docstring correction (no logic changes)

## Test plan

- [x] `python3 -m py_compile retry_utils.py`
- [x] Reviewer confirmed docs-only diff
- [x] Verifier re-ran compile on workspace copy

## Multi-agent notes

| Task | Role | Outcome |
| --- | --- | --- |
| T001 | Explorer | Located typo at docstring line; no other occurrences |
| T002 | Worker | Applied fix; result JSON + this PR body |
| T003 | Reviewer | Scope clean; `required_paths_verified=true` |
| T004 | Verifier | `py_compile` exit 0 |
