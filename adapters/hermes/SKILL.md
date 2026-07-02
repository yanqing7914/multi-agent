---
name: hermes-multi-agent
description: Hermes-specific thin adapter for multi-agent coding over the shared OpenClaw mission-control core. Use when a self-hosted, always-on Hermes Agent (Nous Research, persistent memory + self-improvement) should coordinate scoped Explorer/Worker/Reviewer/Verifier roles, generate task cards, collect JSON+Markdown result reports, run scope audit, and inject the project's MCP coordinator into ~/.hermes/config.yaml. Do not use for simple single-agent edits.
version: 0.1.0
author: multi-agent-coding
license: MIT
metadata:
  hermes:
    tags:
      - multi-agent
      - orchestration
      - mission-control
      - code-review
    related_skills:
      - openclaw-multi-agent
---

# hermes-multi-agent

Thin Hermes adapter over the shared OpenClaw mission-control core. Reuse
`adapters/openclaw/scripts/*` for task cards, gates, audits, and memory; this
skill only adds Hermes-specific wiring (agentskills.io discovery, the native MCP
client, and the persistent-memory / learning-loop integration).

Hermes (Nous Research, 2026) is a self-hosted, always-on agent with persistent
memory and a self-improvement loop. It loads portable `SKILL.md` files in the
[agentskills.io](https://agentskills.io) open standard — the same format this
project uses — so this adapter is discovered natively once installed.

## When To Use

Use when:

- a Hermes Agent acts as Main and the user asks for multiple agents, Workers, Reviewers, Verifiers, or parallel review
- the task spans multiple modules (e.g. backend + frontend + tests) and needs scoped `allowed_paths`
- the work needs task cards, result reports (JSON + Markdown), gate sync, and a final scope/diff audit
- you want Hermes' persistent memory and learning loop to record run outcomes through `MEMORY.md` and the audit gates

Do not use when:

- the task is a quick single-agent edit or a tiny fix
- the task card is unscoped or lacks an output contract
- the user explicitly wants OpenClaw `sessions_spawn`; use `adapters/openclaw/`
- ownership cannot be expressed with clear `allowed_paths`

## Roles And Permission Boundaries

The portable contract is task cards + role permissions + result reports + audit
records. It is identical to every other adapter, so a card produced here is
portable to OpenClaw, Cursor, Codex, or Claude Code.

| Role | Write? | Spawn? | Boundary |
| --- | --- | --- | --- |
| Main | yes (delivery) | yes | Plans, creates cards, dispatches, collects reports, runs gate sync + **scope audit before delivery**. |
| Explorer | no | no | Read-only research and evidence with file paths/line refs. |
| Worker | yes | no | Edits **only inside `allowed_paths`**; never touches `blocked_paths`, secrets, or runs `blocked_commands`. |
| Reviewer | **no (read-only)** | no | Reports findings by severity with evidence; `files_changed` must stay empty; may use review skills (e.g. `ssrd`) only when `may_use_skills` lists them. |
| Verifier | no | no | Runs allowed validation; lists every file in `files_read` (a passing test alone is not evidence). |

Hard rules:

- A Worker that needs to edit outside `allowed_paths`, read a secret, install dependencies, deploy/push, or resolve a conflicting user change must stop and report `status=blocked`.
- A Reviewer is read-only regardless of runtime. If asked to "review with `ssrd`", create Reviewer cards with `may_use_skills: [ssrd]`, never Workers.
- Skills authorized in a card cannot expand `allowed_paths`, shell commands, network access, credentials, git writes, or role permissions.
- Main delivers only after every upstream gate passes and `scope_audit` is `passed`.

## Generate Task Cards And Audit (reuse OpenClaw scripts)

This adapter does **not** duplicate mission-control logic. Call the canonical
scripts under `adapters/openclaw/scripts/` from the target repo root.

Generate cards, ownership, status, and run plan:

```bash
python3 /path/to/hermes-multi-agent/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/hermes-multi-agent/adapters/openclaw/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

Sync gates before each dispatch wave, mark tasks complete, and re-sync:

```bash
python3 .../adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync
python3 .../adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --task-id T002 --status completed
```

Scope audit (Main, before delivery) — `ok=true` counts as passed only when the
audit gate is `passed` (exit 0):

```bash
python3 adapters/openclaw/scripts/capture_changed_files.py --state-dir .codex-multi-agent  # staged + unstaged + untracked
python3 .../adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

Each generated card embeds an absolute `workspace_root`/`target_repo` and a
mandatory `preflight_command` (via `verify_workspace.py`). Every child agent must
`cd` to `workspace_root`, run `pwd` and the preflight, and record
`workspace_observed`, `required_paths_verified`, and `files_read` so
`update_task_status.py --sync` can downgrade false `completed` claims to
`blocked`.

## Wire The MCP Coordinator Into Hermes

Hermes has a native MCP client: any server listed under `mcp_servers` in
`~/.hermes/config.yaml` (stdio or http) is connected at startup, its tools are
auto-discovered and injected as native Hermes tools. Register this project's
coordinator so Main can call `create_task`, `update_task_status`, `audit_scope`,
`record_finding`, etc. on the same `.codex-multi-agent/` state instead of
shelling out.

Add to `~/.hermes/config.yaml` (replace the absolute paths):

```yaml
# ~/.hermes/config.yaml
mcp_servers:
  multi-agent-coordinator:
    transport: stdio
    command: python3
    args:
      - /absolute/path/to/multi-agent-coding/mcp/multi-agent-coordinator/server.py
      - --state-dir
      - .codex-multi-agent
    cwd: /absolute/path/to/your/workspace
    env:
      WORKSPACE: /absolute/path/to/your/workspace
```

If you run the coordinator behind an HTTP gateway instead of stdio, use the http
transport form Hermes also supports:

```yaml
mcp_servers:
  multi-agent-coordinator:
    transport: http
    url: http://127.0.0.1:8765/mcp
```

The MCP layer is optional glue: the portable contract still lives in
`.codex-multi-agent/` task cards and result reports, so the OpenClaw scripts and
the MCP tools operate on exactly the same state.

## Persistent Memory + Learning Loop

Hermes keeps cross-session memory (SQLite FTS5 + LLM summaries) and writes a
skill doc after finishing a complex task. Bind that loop to this project's
auditable, secret-free record so memory reinforces the gates rather than
bypassing them:

- After a run, append the gate/audit/findings outcome to `MEMORY.md` via the shared logger:

```bash
python3 .../adapters/openclaw/scripts/memory_log.py --state-dir .codex-multi-agent --from-run
```

- `create_task_cards.py` seeds each card's `context` with the tail of `MEMORY.md`, so Hermes' recall feeds the next run.
- Hermes' learning loop must treat `MEMORY.md` as **append-only and secret-free**: never store credentials, tokens, or `.env` contents; keep one decision/outcome per line.
- Memory and the self-improvement loop are advisory. Delivery is still gated by `scope_audit` and `status.json`; a remembered "this worked before" never substitutes for a passing audit. Main runs the scope audit after every run before delivering.

## Install Location

Hermes reads the agentskills.io standard skill directories. Install this skill to
both:

```text
~/.agents/skills/hermes-multi-agent
~/.hermes/skills/hermes-multi-agent
```

See `README.md` for the install steps and `QUICKSTART.md` for the Golden Path.

## Validation

```bash
python3 adapters/hermes/scripts/hermes_self_check.py --self-check
python3 adapters/openclaw/scripts/validate_all.py
```
