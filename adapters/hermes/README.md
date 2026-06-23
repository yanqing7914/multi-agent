# Hermes Multi-Agent Adapter

Thin Hermes layer over the [`adapters/openclaw/`](../openclaw/) mission-control
scripts. It does not duplicate task-card generation, gate sync, or audit logic —
it adds the Hermes-specific pieces: agentskills.io discovery, the native MCP
client wiring, and the persistent-memory / learning-loop integration.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## What This Enables

[Hermes](https://agentskills.io) (Nous Research, 2026) is a self-hosted,
always-on agent with persistent memory and a self-improvement loop. It loads
portable `SKILL.md` files in the agentskills.io standard — the same format this
project uses. Once installed, a Hermes Agent acting as Main gets the shared
workflow:

1. Hermes Main receives a multi-agent request.
2. Main generates scoped task cards under `.codex-multi-agent/` with the OpenClaw scripts.
3. Main dispatches Workers/Reviewers/Verifiers under explicit role boundaries.
4. Each agent writes JSON + Markdown result reports.
5. Main runs gate sync, scope audit, memory logging, and final delivery.

## Install

Hermes reads the agentskills.io standard skill directories. Install this skill to
both locations so the App and any CLI/runtime discover it:

```text
~/.agents/skills/hermes-multi-agent
~/.hermes/skills/hermes-multi-agent
```

From the repository root you can copy the adapter (plus the shared OpenClaw
scripts it reuses) into those directories, or let Main's installer handle it. The
skill needs the following alongside it to run end-to-end:

- `adapters/hermes/` (this folder: `SKILL.md`, `README.md`, `QUICKSTART.md`, `scripts/`)
- `adapters/openclaw/scripts/` and `adapters/openclaw/templates/` (shared mission-control core)
- `mcp/multi-agent-coordinator/` (optional MCP coordinator)

After copying, reload Hermes so it re-scans the skill directories and discovers
`hermes-multi-agent`.

## Wire The MCP Coordinator

Hermes connects every server under `mcp_servers` in `~/.hermes/config.yaml` at
startup (stdio or http) and injects their tools as native tools. Point it at this
project's coordinator (`mcp/multi-agent-coordinator/server.py --state-dir
.codex-multi-agent`):

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

The MCP layer is optional glue; the portable state still lives in
`.codex-multi-agent/`, so MCP tools and the OpenClaw scripts share one source of
truth.

## Usage

After the skill is installed and Hermes is reloaded, ask the Hermes Agent:

```text
Use hermes-multi-agent. Split this change into scoped task cards, dispatch Workers and Reviewers under their role boundaries, collect JSON+Markdown result reports, run scope audit, log the run to MEMORY.md, and deliver only after gates pass.
```

Main then drives the shared scripts (see [QUICKSTART.md](QUICKSTART.md)):

```bash
# 1. Generate cards from the target repo root
python3 .../adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml .../adapters/openclaw/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" --out .codex-multi-agent

# 2. Sync gates, run Workers/Reviewers, mark complete
python3 .../adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync

# 3. Scope audit before delivery
git diff --name-only > .codex-multi-agent/changed-files.txt
python3 .../adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent

# 4. Log the run into persistent memory
python3 .../adapters/openclaw/scripts/memory_log.py --state-dir .codex-multi-agent --from-run
```

## Contract

| Artifact | Location |
| --- | --- |
| Task cards | `.codex-multi-agent/tasks/*.md` |
| Result Markdown | `.codex-multi-agent/results/*.md` |
| Result JSON | `.codex-multi-agent/results/*.json` |
| Gate state | `.codex-multi-agent/status.json` |
| Ownership / scope | `.codex-multi-agent/ownership.json` |
| Scope audit records | `.codex-multi-agent/audits/*.json` |
| Persistent memory | `MEMORY.md` (+ `.codex-multi-agent/memory/run-*.md`) |
| Preflight | `adapters/openclaw/scripts/verify_workspace.py` |
| Schema | `adapters/openclaw/templates/result-report.md` |

The portable contract is the task cards, result reports, role names and
permissions, skill-use approvals, review findings, and audit records — not the
Hermes runtime. A card produced here runs unchanged on any other adapter.

## Role Boundaries (must hold)

- **Worker:** edits only inside `allowed_paths`; stops and reports `status=blocked` on scope expansion, secrets, dependency install, or deploy/push.
- **Reviewer:** read-only; empty `files_changed`; review skills (e.g. `ssrd`) only when authorized via `may_use_skills`.
- **Main:** runs gate sync and `scope_audit` (audit gate `passed`, exit 0) before final delivery; memory recall never substitutes for a passing audit.

## Self-check

```bash
python3 adapters/hermes/scripts/hermes_self_check.py --self-check
```

Validates that `SKILL.md`/`README.md`/`QUICKSTART.md` exist, the SKILL.md
frontmatter declares `name`/`description`, and the SKILL.md documents both the
`mcp_servers` wiring and agentskills.io discovery. Dependency-free (stdlib only,
Python 3.10+).
