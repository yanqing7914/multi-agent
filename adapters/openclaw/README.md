# OpenClaw Multi-Agent Adapter

This folder is a self-contained OpenClaw/Her skill. Install or symlink it into your OpenClaw skills directory and invoke `$openclaw-multi-agent` without reading the rest of the root repository.

It focuses on practical OpenClaw session workflows:

- `sessions_spawn` / `sessions_send` / `sessions_yield`
- ACP or native subagent runtime selection
- scoped Worker task cards with explicit gates and handoffs
- read-only Reviewer sessions, including `ssrd`
- v1 mission-control local state under `.codex-multi-agent/`
- script-assisted task-card generation, status tracking, worker audit, and run summary

## Install

**Fast path:** see [QUICKSTART.md](QUICKSTART.md) for copy-paste commands and expected outputs from a fresh checkout.

Copy or symlink this folder into your OpenClaw skills path, for example:

```bash
ln -s /path/to/multi-agent-coding/adapters/openclaw ~/.openclaw/skills/openclaw-multi-agent
```

Then invoke it from OpenClaw/Her:

```text
Use $openclaw-multi-agent to split this feature into Explorer, Worker, Reviewer, and Verifier sessions.
```

中文示例：

```text
使用 $openclaw-multi-agent，把这个功能拆成 Explorer、Worker、Reviewer 和 Verifier 来做。
```

## When To Use

Use for complex multi-role coding tasks:

- multi-module feature work
- large codebase research
- multi-agent review
- SSRD/security review
- complex bug investigation
- refactor with scoped module ownership

Do not use for:

- simple coding tasks
- explicit single-agent tasks routed by `acp-router`
- batch homogeneous jobs handled by `parallel-claude`

## Directory Layout

```text
SKILL.md
README.md
QUICKSTART.md
scripts/create_task_cards.py
scripts/update_task_status.py
scripts/audit_worker_output.py
scripts/verify_workspace.py
scripts/run_local_demo.py
scripts/validate_all.py
templates/task-card.md
templates/result-report.md
templates/ownership.example.json
examples/favorite-feature.yaml
examples/fizzbuzz-module-paths.yaml
examples/fizzbuzz-module-paths.json
examples/dogfood-openclaw.yaml
```

## v1 Mission Control (`.codex-multi-agent/`)

OpenClaw v1 works **without MCP**. Main stays accountable by reading/writing local state:

```text
.codex-multi-agent/
  status.json          # gate + task status
  ownership.json       # path ownership
  run-plan.json        # ordered workflow phases
  tasks/               # task cards (portable contract)
  results/             # JSON + Markdown result reports
  findings/            # aggregated reviewer findings
  approvals/           # skill-use approvals (manual in v1)
  audits/              # scope audit JSON
  summary/             # run-summary.md
  changed-files.txt    # optional git diff list
```

Keep it local-only unless the user explicitly wants it committed.

## Quick Start

1. From the **target repo root**, generate task cards, ownership, status, and run plan:

```bash
python /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/multi-agent-coding/adapters/openclaw/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

Expected JSON includes `"ok": true` and `"workspace_root": "/absolute/path/to/target-repo"`.

**Module path mapping:** Known modules (`backend`, `frontend`, `tests`, etc.) map to default globs. For custom layouts (e.g. `src/**` + `tests/**`), supply explicit paths per module:

```yaml
modules:
  - name: fizzbuzz
    paths:
      - src/**
      - tests/**
```

Or use `--from-json` with the same shape (`examples/fizzbuzz-module-paths.json`). Unknown module names without explicit `paths` default to `{name}/**` and the generator adds a `warnings` field suggesting explicit paths.

2. Sync status before each spawn wave:

```bash
python scripts/update_task_status.py --state-dir .codex-multi-agent --sync
```

3. Spawn OpenClaw sessions using names in the generated cards, e.g. `explorer-backend`, `worker-frontend`, `reviewer-security`, `verifier`.

4. Send each card with `sessions_send`, then `sessions_yield` while waiting for the child session.

5. Require each session to write both result files listed in `result_report_paths`:

```text
.codex-multi-agent/results/T002-worker-backend.json
.codex-multi-agent/results/T002-worker-backend.md
```

6. Mark tasks complete and resync gates:

```bash
python scripts/update_task_status.py --state-dir .codex-multi-agent --task-id T002 --status completed
python scripts/update_task_status.py --state-dir .codex-multi-agent --sync
```

7. Capture changed files and audit Worker scope:

```bash
python3 adapters/openclaw/scripts/capture_changed_files.py --state-dir .codex-multi-agent  # staged + unstaged + untracked

python scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit \
  --state-dir .codex-multi-agent
```

8. Summarize the run for final delivery:

```bash
python scripts/update_task_status.py --state-dir .codex-multi-agent --summarize
```

9. Main performs diff audit, integrates results, and delivers the final answer.

## Golden Path (end-to-end)

This is the reproducible dogfood sequence Main should follow:

| Step | Action | Success signal |
| --- | --- | --- |
| 0 | `cd` to target repo; pass `--workspace-root "$(pwd)"` to generator | Task cards show absolute `workspace_root` |
| 1 | `create_task_cards.py` → `.codex-multi-agent/` | `ownership.json`, `status.json`, `tasks/*.md` exist |
| 2 | `update_task_status.py --sync` | `current_phase` reflects first incomplete gate |
| 3 | Spawn Explorer(s); child runs `preflight_command` then work | JSON+MD under `results/` |
| 4 | `--sync` after Explorer wave | `explorers_complete` → `passed` |
| 5 | Spawn Worker(s) in scope | `files_changed` lists business code only (not `.codex-multi-agent/results/*`) |
| 6 | `git diff` → `changed-files.txt`; `audit_worker_output.py --write-audit` | `audits/latest.json` with `"ok": true` and `gate.status=passed` (exit 0) |
| 7 | Spawn Reviewer(s) after Workers | `files_read` populated; `files_changed` empty |
| 8 | `--sync`; triage `findings/review-findings.json` | `review_complete` → `passed` |
| 9 | Spawn Verifier; `--sync`; `--summarize` | `files_read` populated (not just pytest pass); `summary/run-summary.md` ready |

**Local proof without agents:**

```bash
python3 scripts/validate_all.py
python3 scripts/run_local_demo.py --keep   # uses a system temp dir by default; pass --out to pin a path
```

## Workspace / cwd (critical)

Dogfood showed Reviewers completing in the **wrong workspace** while reporting `status=completed`. v1 fixes:

- Every generated card includes `workspace_root`, `target_repo`, and `preflight_command`.
- Subagents must `cd` to the absolute `workspace_root` **before** any reads (do not rely on `sessions_spawn` cwd).
- `verify_workspace.py` checks that required path prefixes exist on disk.
- `update_task_status.py --sync` downgrades `completed` → `blocked` when:
  - `required_paths_verified=false`, or
  - `required_paths_missing` is non-empty, or
  - `workspace_observed` does not match `ownership.json` `workspace_root`, or
  - **thin evidence:** Reviewer/Explorer/Verifier claims verification but `files_read` is empty for concrete `required_paths`.
- Preflight uses **absolute** paths to `verify_workspace.py` (works when the skill is symlinked outside the target repo).

Wrong workspace → `status=blocked` in the result report, not fake findings.

## Workflow Gates

Each task card includes `gate`, `dependencies`, and `main_commands`. Main must not skip gates:

```text
Explorer -> Worker -> Reviewer -> Verifier -> scope_audit -> final_delivery
```

| Gate | Pass when |
| --- | --- |
| `explorers_complete` | All Explorer result reports exist and none report `status=completed` without `required_paths_verified=true` |
| `workers_complete` | All Worker result reports exist and preflight fields confirm required paths were readable |
| `review_complete` | All Reviewer result reports exist and preflight fields confirm required paths were readable |
| `verify_complete` | Verifier result report exists and preflight fields confirm required paths were readable |
| `scope_audit` | Latest audit JSON has `"ok": true`, `gate.status=passed`, and `changed-files.txt` digest matches the audit (not stale) |
| `final_delivery` | All upstream gates passed; Main delivers |

## Scope audit semantics

- `audit_worker_output.py` sets **`ok=true` only when `gate.status=passed`**. Warnings (missing Worker reports, unowned paths in non-strict mode) yield `ok=false`, `gate.status=pending`, and exit code `2`.
- `--write-audit` records `changed_files_digest` / `changed_files_mtime` from `changed-files.txt` (or an empty digest if the file is absent).
- `update_task_status.py --sync` treats the latest audit as **stale** when `changed-files.txt` changes or lacks matching digest metadata; `scope_audit` stays `pending` and `latest_audit.ok` is `false`.
- Do not commit mission-control dirs under `adapters/openclaw/` (`.tmp-openclaw-test`, `.codex-multi-agent`, etc.). `validate_all.py` fails if they are present.

## Anti-False-Completion Rule (Hard)

Dogfood found that Reviewers can report `status=completed` from the wrong workspace while never reading the requested files. This adapter now treats that as a **hard gate failure**, not a successful review.

Every generated task card includes:

- `workspace_root` / `target_repo` (absolute path to the repo under change)
- `preflight_command` (shell lines including `verify_workspace.py`)
- `required_paths` derived from module focus (`openclaw_adapter` maps to `adapters/openclaw/**`; custom modules need explicit `paths:` in YAML/JSON)
- mandatory preflight + workspace guidance in `execution_guidance`
- gate rules that forbid `status=completed` unless `required_paths_verified=true` and evidence is credible

Every result report must include:

- `workspace_observed` (output of `pwd` after `cd` to `workspace_root`)
- `required_paths_checked` / `required_paths_missing`
- `required_paths_verified: true|false`
- `files_read` (non-empty for Reviewer/Explorer/Verifier when concrete paths were required; test pass alone is not enough)

When `update_task_status.py --sync` sees false or thin completion, it downgrades the task to `blocked` and gates fail. The run summary lists these under **Workspace / Preflight Issues**.

If a subagent is in the wrong workspace, it must set `status=blocked` with the missing paths — never fake findings on unread files.

Task cards describe explicit OpenClaw commands (`sessions_spawn`, `sessions_send`, `sessions_yield`) and script commands Main should run. Scripts update state files; they do not spawn sessions.

## Runtime Selection

- `runtime=acp`: route the child session to an ACP-backed coding agent.
- `runtime=subagent` or `runtime=native`: use OpenClaw's own session runtime.
- Reviewer sessions stay read-only regardless of runtime.

## Worker vs Reviewer

- Workers may edit only inside `allowed_paths` and must produce result reports with accurate `files_changed`.
- Reviewers are read-only, must keep `files_changed` empty, and may use review skills such as `ssrd` only when authorized in the task card.

## Script Self-Checks

Run these from this folder:

```bash
python3 scripts/validate_all.py
```

## Manual Templates

If you do not use the generator, copy:

- `templates/task-card.md` for delegation
- `templates/result-report.md` for child session output
- `templates/ownership.example.json` for the ownership schema expected by the audit script

## Roadmap

v1 (this adapter): prompt + scripts + `.codex-multi-agent/` local state.

v2: MCP state server — see [`../../docs/mcp-format.md`](../../docs/mcp-format.md).

v3: IDE task panel — see [`../../docs/roadmap.md`](../../docs/roadmap.md).

## Example Task Definition

See `examples/favorite-feature.yaml`:

```yaml
task: Add vehicle favorite feature
mode: implement
modules:
  - backend
  - frontend
  - tests
reviewers:
  - correctness
  - security
skills:
  reviewer:
    - ssrd
```

Generate cards from it with:

```bash
python scripts/create_task_cards.py --from-yaml examples/favorite-feature.yaml --out .codex-multi-agent
```
