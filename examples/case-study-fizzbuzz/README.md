# Case study: FizzBuzz multi-agent run (all gates green)

End-to-end narrative for the OpenClaw FizzBuzz / mission-control dogfood run that exercised Explorer → Worker → Reviewer → Verifier gates with real safety findings and fixes.

## Goal

Validate v1 mission-control gates on a small feature (`FizzBuzz` module) while dogfooding the OpenClaw adapter scripts (`create_task_cards`, `update_task_status`, `audit_worker_output`, `run_local_demo`).

## Commands (Golden Path)

```bash
# 1) Generate task cards
python3 adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml adapters/openclaw/examples/fizzbuzz-module-paths.yaml \
  --out .codex-multi-agent \
  --workspace-root "$(pwd)"

# 2) Sync gates after each role completes
python3 adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync

# 3) Worker phase: capture diff + audit
git diff --name-only > .codex-multi-agent/changed-files.txt
python3 adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent

# 4) Summarize for Main (+ MEMORY.md append)
python3 adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --summarize
```

Real dogfood snapshots (paths neutralized to `<repo>`) live in:

- [`cards/`](cards/) — T001–T004 task cards
- [`results/`](results/) — JSON/Markdown result reports
- [`summary/run-summary.md`](summary/run-summary.md) — final gate snapshot

## Expected JSON shapes

### Task status (`status.json` excerpt)

```json
{
  "run_id": "20260525T064400Z",
  "current_phase": "final_delivery",
  "gates": {
    "explorers_complete": { "status": "passed" },
    "workers_complete": { "status": "passed" },
    "review_complete": { "status": "passed" },
    "verify_complete": { "status": "passed" },
    "scope_audit": { "status": "passed" },
    "final_delivery": { "status": "passed" }
  }
}
```

### Worker result report (minimum)

```json
{
  "task_id": "T002",
  "role": "Worker",
  "status": "completed",
  "workspace_observed": "<repo>",
  "required_paths_verified": true,
  "files_read": ["src/fizzbuzz.py"],
  "tools_used": ["repo_index_tool", "test_runner_tool"],
  "files_changed": ["src/fizzbuzz.py"]
}
```

### Audit JSON (`audits/latest.json` excerpt)

```json
{
  "ok": true,
  "gate": { "id": "scope_audit", "status": "passed" },
  "violations": [],
  "warnings": []
}
```

## Seven real findings we caught and fixed

1. **Malformed reviewer JSON crashes status sync** — `sync_status` now skips bad JSON with a structured finding instead of crashing.
2. **Invalid status tokens coerced to completed** — unknown status strings downgrade to `blocked` (`invalid_status_token`).
3. **False completion** — `required_paths_verified=false` cannot pass as `completed` (`false_completion`).
4. **Thin evidence** — Reviewer/Verifier `completed` with empty `files_read` blocks gates (`thin_evidence`).
5. **Workspace mismatch** — `workspace_observed` must match `workspace_root` (`workspace_mismatch`).
6. **Stale audit** — `changed-files.txt` digest must match latest audit metadata (`stale_audit`).
7. **Missing JSON result + mission-control noise** — Markdown-only reports block gates (`missing_result_report_json`); Worker `files_changed` must not list `.codex-multi-agent/results/*` (`mission_control_exempt`).

## Lessons learned

- Treat **result JSON** as the source of truth; Markdown is a companion only.
- Preflight + `files_read` evidence is not optional for Reviewer/Verifier roles.
- Scope audit must reconcile **git changed-files** with Worker ownership, not just result reports.
- Self-check fixtures in each script prevented regressions when fixing the above gates.

## Related

- Example task definition: [`adapters/openclaw/examples/fizzbuzz-module-paths.yaml`](../../adapters/openclaw/examples/fizzbuzz-module-paths.yaml)
- Local demo: `python3 adapters/openclaw/scripts/run_local_demo.py --self-check`
