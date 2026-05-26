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

## Real run — Claude Code via ACP

A live Claude Code worker run (via ACP, no Anthropic API quota consumed) was captured at `examples/case-study-flask-cli/.runs/claude-code-real-20260526T020911Z/`. Because the `/version` task was already on `main`, the worker picked a structurally equivalent but **new** scope — add a `/ping` endpoint returning `{"pong": true}` plus a unit test — so the run produces an actual diff and exercises the full Worker contract end-to-end (preflight → scoped edits in `app/**` + `tests/**` → `pytest` 4 passed → result JSON/MD → `audit_worker_output.py` `ok: true`). This closes the roadmap gap "Claude Code 本地真 dogfood 全闭环" for the ACP path.

| Artifact | Location |
| --- | --- |
| Worker task card | `.runs/claude-code-real-20260526T020911Z/tasks/T100-worker-app.md` |
| Worker JSON report | `.runs/claude-code-real-20260526T020911Z/results/T100-worker-app.json` |
| Worker Markdown report | `.runs/claude-code-real-20260526T020911Z/results/T100-worker-app.md` |
| Diff patch | `.runs/claude-code-real-20260526T020911Z/changes.patch` |
| Ownership map | `.runs/claude-code-real-20260526T020911Z/ownership.json` |
| Scope audit output | `.runs/claude-code-real-20260526T020911Z/audit-output.json` |
| Latest written audit | `.runs/claude-code-real-20260526T020911Z/audits/latest.json` |

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

## Cross-IDE relay (2026-05-26)

第一次真实的「跨 IDE 接力」：同一个任务卡 + 同一份 ownership 在三家 IDE 间流转，
schema 一致、gate 全通。

| Step | Runtime | 角色 | 产物 |
| --- | --- | --- | --- |
| 1 | OpenClaw Main | Mission control | `../../.codex-multi-agent-relay/{ownership,run-plan}.json` |
| 2 | Cursor (PTY/tmux) | Worker R001 — 实现 `/echo` | `../../.codex-multi-agent-relay/results/R001-worker-echo.{json,md}` |
| 3 | Claude Code (ACP) | Reviewer R002 — 评审 + 5 finding | `../../.codex-multi-agent-relay/results/R002-reviewer-echo.{json,md}` |
| 4 | OpenClaw Main | scope_audit + final delivery | `../../.codex-multi-agent-relay/audits/latest.json` (ok=true) |

完整 run summary：[`../../.codex-multi-agent-relay/summary/run-summary.md`](../../.codex-multi-agent-relay/summary/run-summary.md)

**Worker Cursor 真改了 3 个文件**（routes.py / server.py / test_routes.py），加了 `/echo?msg=...` 端点 + 3 个单元测试，pytest 7/7 通过。
**Reviewer Claude Code 真读了代码**，找出 5 个 finding（2 P2 / 3 P3），verdict=`approved_with_findings`。
**OpenClaw Main audit 真过 gate**，violations=0, conflicts=0, warnings=0。

这是项目「跨 IDE 协作契约」目标的端到端证据。

## Related

- Single-module case study: [`../case-study-fizzbuzz/`](../case-study-fizzbuzz/)
- Cross-IDE relay artifacts: [`../../.codex-multi-agent-relay/`](../../.codex-multi-agent-relay/)
- Bench harness: [`../../bench/swebench-lite/`](../../bench/swebench-lite/)
