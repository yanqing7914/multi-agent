# Hermes Multi-Agent Quickstart

Dependency-free Python 3. Reuses the OpenClaw mission-control scripts. This is the
Golden Path: install the skill, wire the MCP server, generate cards, run
Worker/Reviewer, then gate sync + scope audit.

## 0. Install The Native Skill

Hermes reads the agentskills.io standard skill directories. Place this adapter
(plus the shared OpenClaw scripts/templates it reuses) into both:

```text
~/.agents/skills/hermes-multi-agent
~/.hermes/skills/hermes-multi-agent
```

Reload Hermes so it discovers `hermes-multi-agent`, then ask the Agent:

```text
Use hermes-multi-agent. Split this into scoped task cards, run Workers and read-only Reviewers, collect result reports, run scope audit, log to MEMORY.md, and deliver only after gates pass.
```

## 1. Configure The MCP Server In ~/.hermes/config.yaml

Hermes connects every `mcp_servers` entry at startup (stdio or http) and injects
its tools natively. Point it at this project's coordinator:

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

Optional glue only: the portable state still lives in `.codex-multi-agent/`.

## 2. Generate Task Cards

From the target repo root (reuses the OpenClaw script):

```bash
python3 /path/to/hermes-multi-agent/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/hermes-multi-agent/adapters/openclaw/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

Each card carries an absolute `workspace_root`/`target_repo` and a mandatory
`preflight_command`. Children must `cd` there, run `pwd` + preflight, and record
`workspace_observed`, `required_paths_verified`, and `files_read`.

## 3. Run Workers / Reviewers

Sync gates before each wave:

```bash
python3 /path/to/hermes-multi-agent/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync
```

Dispatch each task card to a Hermes child agent under its role boundary:

- **Worker** — edits only inside `allowed_paths`; writes both result files in `result_report_paths`; stops with `status=blocked` on scope expansion, secrets, dependency install, or deploy/push.
- **Reviewer** — read-only; empty `files_changed`; uses review skills (e.g. `ssrd`) only when `may_use_skills` lists them.

Mark each task complete and re-sync:

```bash
python3 /path/to/hermes-multi-agent/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --task-id T002 --status completed
python3 /path/to/hermes-multi-agent/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync
```

`--sync` downgrades a false `completed` to `blocked` when
`required_paths_verified=false` or evidence is thin.

## 4. Gate Sync + Scope Audit

Main audits scope before delivery (`ok=true` counts as passed only when the audit
gate is `passed`, exit 0):

```bash
git diff --name-only > .codex-multi-agent/changed-files.txt
python3 /path/to/hermes-multi-agent/adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

Summarize the run for delivery:

```bash
python3 /path/to/hermes-multi-agent/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --summarize
```

## 5. Log Persistent Memory

Append the run's gates/audit/findings outcome to `MEMORY.md` (append-only,
secret-free) so Hermes' memory and learning loop reinforce the gates:

```bash
python3 /path/to/hermes-multi-agent/adapters/openclaw/scripts/memory_log.py \
  --state-dir .codex-multi-agent --from-run
```

## Self-check

```bash
python3 /path/to/hermes-multi-agent/adapters/hermes/scripts/hermes_self_check.py --self-check
python3 /path/to/hermes-multi-agent/adapters/openclaw/scripts/validate_all.py
```
