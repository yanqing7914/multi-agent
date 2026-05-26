# Case study: multi-file Flask-shaped CLI (stdlib only)

Multi-file example under `app/` with real pytest. Uses `http.server` + `argparse` — no Flask dependency.

## End-to-end (Codex runtime)

From the **repository root**:

```bash
python3 scripts/run_multi_agent.py \
  --runtime codex \
  --task-card examples/case-study-flask-cli/.codex-multi-agent/tasks/T002-worker-app.md
```

Generate cards first if needed:

```bash
python3 adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml examples/case-study-flask-cli/task.yaml \
  --out examples/case-study-flask-cli/.codex-multi-agent \
  --workspace-root "$(pwd)/examples/case-study-flask-cli" \
  --runtime codex
```

## Expected outputs (after a successful run)

| Artifact | Location |
| --- | --- |
| Task cards | `examples/case-study-flask-cli/cards/` (copy or symlink from `.codex-multi-agent/tasks/`) |
| Result reports | `examples/case-study-flask-cli/results/` |
| Run summary | `examples/case-study-flask-cli/summary/run-summary.md` |

Gates should progress through Explorer → Worker → Reviewer → Verifier when all roles complete with valid JSON reports.


## Real Codex run captured

A live Codex worker run was captured at `examples/case-study-flask-cli/.runs/codex-real-20260526T015459Z/`.

| Artifact | Location |
| --- | --- |
| Worker task card copy | `examples/case-study-flask-cli/.runs/codex-real-20260526T015459Z/tasks/T002-worker-app.md` |
| Worker JSON report | `examples/case-study-flask-cli/.runs/codex-real-20260526T015459Z/results/T002-worker-app.json` |
| Worker Markdown report | `examples/case-study-flask-cli/.runs/codex-real-20260526T015459Z/results/T002-worker-app.md` |
| Scope audit output | `examples/case-study-flask-cli/.runs/codex-real-20260526T015459Z/audit-output.json` |
| Latest written audit | `examples/case-study-flask-cli/.runs/codex-real-20260526T015459Z/audits/latest.json` |

Result: Codex reported the `/version` work was already present, ran `pytest -q tests/test_routes.py` successfully (`3 passed`), wrote JSON + Markdown reports, and `audit_worker_output.py` passed with `ok: true`.

## Local verification (no agent)

```bash
cd examples/case-study-flask-cli
PYTHONPATH=. pytest tests -q
python3 -m app.cli run --help
```

## Caveats

- **Requires Codex CLI + auth** for the live `--runtime codex` path; use OpenClaw `--self-check` demos for offline validation.
- Worker must stay within `app/**` and `tests/**` allowed paths.
- HTTP server test is manual (`python3 -m app.cli run`); automated tests cover route payloads only.
- `cards/`, `results/`, `summary/` start empty — populated when you run the workflow.

## Related

- Single-module case study: [`../case-study-fizzbuzz/`](../case-study-fizzbuzz/)
- Bench harness: [`../../bench/swebench-lite/`](../../bench/swebench-lite/)
