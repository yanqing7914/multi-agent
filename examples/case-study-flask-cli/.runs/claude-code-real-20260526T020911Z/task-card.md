# Task card (copy)

This is the input task card the Claude Code (ACP) worker ran against.

Source: hand-authored for this run. See `tasks/T100-worker-app.md` (same content) for
the machine-readable copy.

## Why hand-authored

The case study's existing T002 worker card targets the `/version` endpoint, which is
already implemented on `main` — Codex confirmed this in its parallel run at
`.runs/codex-real-20260526T015459Z/` with `files_changed: []`. To prove the Claude
Code adapter actually closes the loop (i.e. a worker can read, edit, validate, and
report), we picked a structurally identical but **distinct** scope: add a `/ping`
endpoint returning `{"pong": true}` plus a unit test.

## Scope

- Allowed paths: `app/**`, `tests/**`
- Required paths verified before edits: same
- Validation: `PYTHONPATH=. pytest tests -q`

## Acceptance

- `ping_payload()` exists in `app/routes.py`
- `GET /ping` returns the payload via `app/server.py`
- `tests/test_routes.py::test_ping_payload` passes
- Full pytest suite stays green
