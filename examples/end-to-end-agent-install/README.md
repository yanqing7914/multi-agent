# End-to-End: GitHub Link To Multi-Agent Run

This demo shows the product goal:

> A user sends `https://github.com/yanqing7914/multi-agent` to their agent and says "install this multi-agent skill". The agent picks the right client package, installs it into the native skill directory, runs a four-end readiness check, wires the MCP coordinator, and then drives a scoped, verifier-gated multi-agent run.

## Scenario

The user is in a target repository and asks:

```text
Install this skill and use multiple agents to review and improve this feature:
https://github.com/yanqing7914/multi-agent
Use ssrd for read-only review if available.
```

## Expected Agent Flow

1. Open the repository README.
2. Read `docs/agent-install.md`.
3. Detect the client surface and pick the matching package (release assets are named `<package>-v<version>.zip`; resolve `<version>` from `releases/latest`). The package base names come from `scripts/build_skill_packages.py`:

   | Client surface | Package base name |
   | --- | --- |
   | Codex App / CLI | `codex-multi-agent-skill` |
   | Cursor App / CLI | `cursor-multi-agent-pack` |
   | Claude Code App / IDE / CLI | `claude-code-multi-agent-pack` |
   | OpenClaw / Her | `openclaw-multi-agent-skill` |
   | Hermes (agentskills.io + native MCP) | `hermes-multi-agent-pack` |
   | Generic / protocol only | `multi-agent-coding-skill` |

4. Run the native installer (and re-check):

```bash
python3 scripts/install_native_skills.py --client all --scope primary --force
python3 scripts/install_native_skills.py --client all --check
```

5. Run the friendly four-end readiness report and finish any "下一步" hints it prints.
6. Register the MCP coordinator (dry-run first, then `--write`).
7. Generate `.codex-multi-agent/` task cards in the target repo.
8. Drive Workers under the right surface, then close the loop with a verifier-gated `run_loop` and a scope audit:
   - Codex App/CLI: native subagents first (`--runtime codex-native`), optional `--runtime codex` bridge
   - Cursor App/CLI: native skill plus `agent` CLI bridge (`--runtime cursor`)
   - Claude Code App/CLI: bundled subagents first, optional `--runtime claude-code` bridge
   - OpenClaw / Her: `sessions_spawn` / `sessions_send` workflow (`--runtime openclaw`)
   - Hermes: native MCP client + the bundled OpenClaw mission-control scripts (`--runtime hermes`)
9. Require every Worker/Reviewer/Verifier to write JSON and Markdown result reports.
10. Run gate sync and scope audit before final delivery.

## Step 1 — Install And Self-Check Four Ends

`doctor.py` is a friendlier companion to `install_native_skills.py --check`. It inspects four ends — **Codex, Cursor, Claude Code, and Hermes** — for native skill install, bundled native subagent files, App/CLI tooling on PATH, and complete Worker readiness, then prints Chinese remediation hints. (OpenClaw is the orchestration runtime itself, not a doctor target.)

```bash
# Install all adapters present in this package, then verify
python3 scripts/install_native_skills.py --client all --scope primary --force
python3 scripts/install_native_skills.py --client all --check

# Friendly four-end report with Chinese next-steps (exits 0; it is a diagnostic)
python3 scripts/doctor.py

# One client only, or machine-readable JSON
python3 scripts/doctor.py --client hermes
python3 scripts/doctor.py --json

# Deterministic pass/fail gate for CI (no machine dependence)
python3 scripts/doctor.py --self-check
```

## Step 2 — Configure MCP (Default Dry-Run, `--write` To Apply)

`configure_mcp.py` turns the per-client templates in `mcp/multi-agent-coordinator/clients/` into a ready-to-use config. **It defaults to `--dry-run`: it prints exactly what would be written and touches nothing.** Pass `--write` to apply. Run it from a full clone of the repository (it needs the `mcp/` templates, which ship in the repo, not in the single-client packs).

```bash
# DRY-RUN (default): preview the merge/paste-block, write nothing
python3 scripts/configure_mcp.py --client cursor --workspace .

# Apply: JSON clients (cursor, claude) are merged in place, preserving existing mcpServers
python3 scripts/configure_mcp.py --client cursor --workspace . --write

# All four MCP clients at once (still dry-run unless --write)
python3 scripts/configure_mcp.py --client all --workspace .

# Deterministic logic check
python3 scripts/configure_mcp.py --self-check
```

Notes:

- `--client` is one of `all`, `cursor`, `claude`, `codex`, `hermes`. `--scope` is `project` (default) or `user`.
- Cursor and Claude Code are JSON configs and are auto-merged on `--write`.
- Codex (`~/.codex/config.toml`) and Hermes (`~/.hermes/config.yaml`) are print-only: the command emits a paste-ready `toml_block` / `yaml_block` instead of auto-editing, to avoid corrupting TOML/YAML.

## Step 3 — Generate Task Cards

From the target repo root (cards, ownership, status, and run-plan land in `.codex-multi-agent/`):

```bash
python3 adapters/openclaw/scripts/create_task_cards.py \
  --task "Implement and review a small feature" \
  --mode implement \
  --modules backend tests \
  --reviewers correctness security \
  --review-skill ssrd \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

With `--modules backend tests` this emits one Explorer + Worker per module, the two Reviewers, and a Verifier — so the backend Worker card is `.codex-multi-agent/tasks/T002-worker-backend.md`.

## Step 4 — Run One Worker Pass

Pick the surface that matches the client (see the runtime list in Step 8 above). For example, the OpenClaw handoff:

```bash
python3 scripts/run_multi_agent.py \
  --runtime openclaw \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

## Step 5 — Verifier-Gated Loop (`run_loop`)

`run_loop.py` runs *loop engineering*: a **Worker (maker)** produces one change per round via `run_multi_agent.py`, an **independent verifier (checker)** judges it (`--verify-command`, optionally AND-ed with the scope audit via `--with-audit`), failures feed back as repair signals, and the loop stops only when the verifier passes **or** the hard `--max-iterations` budget is hit. The producer may never grade itself (maker ≠ checker is enforced).

```bash
# Deterministic, no-side-effect demo (great for a smoke test / CI):
python3 adapters/openclaw/scripts/run_loop.py --self-check

# Real, bounded, verifier-gated convergence loop:
python3 adapters/openclaw/scripts/run_loop.py \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --runtime openclaw \
  --verify-command "pytest -q" \
  --with-audit \
  --max-iterations 5 \
  --state-dir .codex-multi-agent
```

This is the automated form of "run a Worker, then verify": `run_loop` re-dispatches the same Worker card as its maker each round, so Step 4 is optional. See [`../case-study-loop/`](../case-study-loop/) for the full loop-engineering walkthrough.

## Step 6 — Scope Audit And Delivery

Main runs the authoritative scope audit before delivery (`ok=true` only when the audit gate is `passed`):

```bash
python3 adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync

python3 adapters/openclaw/scripts/capture_changed_files.py --state-dir .codex-multi-agent  # staged + unstaged + untracked
python3 adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

`run_loop --with-audit` already layers this audit into the loop's stop condition; this final pass is Main's independent sign-off on the full diff before delivery.

## What This Proves

- A GitHub link is enough for an agent to find installation instructions and pick the right package across six surfaces (Codex, Cursor, Claude Code, OpenClaw, Hermes, generic).
- `doctor.py` gives a single four-end readiness verdict (Codex / Cursor / Claude Code / Hermes) with concrete remediation, and a deterministic `--self-check` gate.
- `configure_mcp.py` is safe by default (dry-run); MCP registration only changes files with explicit `--write`, and never auto-rewrites TOML/YAML.
- Codex, Cursor, Claude Code, OpenClaw, and Hermes all share the same task-card + ownership + result-report + audit contract.
- The verifier-gated `run_loop` makes Worker → independent verify + audit → repair converge automatically, with maker ≠ checker and a hard iteration budget (never an unbounded loop).
- Main remains accountable for gate sync, scope audit, and final delivery.
