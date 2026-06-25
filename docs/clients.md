# Client Support Model

This project targets a shared multi-agent coordination protocol across **Codex**, **Cursor**, **Claude Code**, **OpenClaw**, Hermes, and VS Code.

**Status:** Codex, Cursor, and Claude Code have client-native skill packages. Codex and Claude Code include native subagent definitions. Cursor ships native Agent Skills; in Cursor App the Main agent dispatches Workers by spawning Cursor subagents directly (in-App delegation, no external CLI), with the `agent` CLI bridge, `/multitask`, and headless/`@cursor/sdk` as alternatives. OpenClaw/Her remains the canonical mission-control reference implementation. Hermes ships a thin adapter (`hermes-multi-agent`) that reuses the OpenClaw mission-control core through Hermes's native MCP client (`~/.hermes/config.yaml`). VS Code stays a protocol + panel scaffold.

## Support layers

| Layer | Purpose | Required everywhere |
| --- | --- | --- |
| Native skill layer | Client-discoverable instructions and trigger metadata | Yes for Codex/Cursor/Claude/OpenClaw/Hermes |
| Mission-control state | Task cards, ownership, status, reports, audits | Yes |
| Worker execution layer | Native subagents or CLI bridge | Client-specific |
| MCP coordination layer | Shared task state, findings, approvals, and scope checks | Optional |
| IDE panel layer | Visual task board over `.codex-multi-agent/` | Optional |

## Compatibility Principle

The portable contract is not the UI or agent runtime. The portable contract is:

- Task cards
- Result reports (JSON + Markdown)
- Role names and permissions
- Skill-use approvals
- Review findings
- Scope and diff audit records
- Final delivery format

Each client may implement spawning, permissions, and tool calls differently.

## v0.2 Client Matrix

| Client | Native skill | App full mode | CLI full mode | Worker launch | Status |
| --- | --- | --- | --- | --- | --- |
| Codex | `codex-multi-agent` | Native Codex subagents + bundled custom agents | Native subagents or `codex exec` bridge | `codex-native` / `codex` | **v0.2 in** |
| Cursor | `cursor-multi-agent` | Native Agent Skill + in-App subagent delegation | delegation, or optional `agent -p` bridge | `cursor` | **in: in-App delegation; CLI bridge optional** |
| Claude Code | `claude-code-multi-agent` | Native skill + bundled `.claude/agents` | Native subagents or `claude --print` bridge | `claude-code` | **v0.2 in** |
| OpenClaw / Her | `openclaw-multi-agent` | `sessions_spawn` / `sessions_send` / `sessions_yield` | Runtime-specific | `openclaw` / ACP | **v1 canonical** |
| Hermes | `hermes-multi-agent` | Native agentskills.io skill + native MCP tools | Native MCP tools + mission-control scripts | `hermes` (MCP) | **v0.2 in** |
| VS Code | Protocol + panel | Extension/MCP dependent | CLI dependent | MCP/panel planned | scaffold |

**Cross-adapter entrypoint:** `scripts/run_multi_agent.py --runtime <name> --task-card <path>`.

**Validation:** `scripts/validate_all_adapters.py` runs OpenClaw checks, the per-client checks, and the self-checks for the native installer, doctor, `configure_mcp`, the Hermes adapter, the loop engine (`run_loop.py`), and the Cursor SDK prep (`prepare_cursor_sdk.py`).

**Readiness diagnostic:** `scripts/doctor.py` reports, per client (Codex / Cursor / Claude Code / Hermes), whether the native skill is installed, whether bundled native agents exist, whether the App/CLI tooling is present, and prints Chinese "下一步" hints. Add `--json` for machine output or `--self-check` for a deterministic pass/fail gate.

**One-step MCP registration:** `scripts/configure_mcp.py --client all` (default dry-run; `--write` to persist) merges the coordinator into Cursor/Claude JSON configs and prints paste-ready blocks for Codex TOML and Hermes YAML (`~/.hermes/config.yaml`).

## Adapter Layout

```text
adapters/
  openclaw/          # canonical mission-control scripts + OpenClaw session mapping
                     #   scripts/run_loop.py = verifier-gated self-correction loop
  cursor/            # native Cursor skill + agent CLI bridge + rules
                     #   scripts/prepare_cursor_sdk.py, sdk/, SDK.md = native SDK/headless paths
  codex/             # native Codex skill + custom agents + codex exec bridge
  claude-code/       # native Claude skill + subagents + claude bridge / ACP
  hermes/            # native agentskills.io skill; reuses OpenClaw core via Hermes MCP client
  _shared/           # bridge.py, self_check.py
scripts/
  install_native_skills.py   # installs native skills (codex/cursor/claude/hermes)
  run_multi_agent.py         # cross-adapter launcher (incl. --runtime hermes)
  configure_mcp.py           # one-step MCP coordinator registration
  doctor.py                  # 4-client readiness report (Chinese 下一步)
  validate_all_adapters.py
tools/
  worktree_tool.py           # one git worktree+branch per Worker (physical isolation)
```

Source of truth remains root `SKILL.md`, `templates/`, `checklists/`, `examples/`, and `docs/mcp-format.md`.

## Behavior By Client

### Codex

- Install `codex-multi-agent-skill-v0.3.1.zip` or run `scripts/install_native_skills.py --client codex` from the repo.
- Native skill dirs: `~/.agents/skills/codex-multi-agent`, `~/.codex/skills/codex-multi-agent`.
- Native custom agents: `~/.codex/agents/multi-agent-worker.toml`, `~/.codex/agents/multi-agent-reviewer.toml`.
- App full mode: Main uses native subagents after the user asks for multi-agent work.
- CLI bridge: `scripts/run_multi_agent.py --runtime codex --task-card ...`.

### Cursor

- Install `cursor-multi-agent-pack-v0.3.1.zip` or run `scripts/install_native_skills.py --client cursor` from the repo.
- Native skill dirs: `~/.agents/skills/cursor-multi-agent`, `~/.cursor/skills/cursor-multi-agent`.
- **Primary (App): in-App subagent delegation.** The Main agent dispatches each Worker/Reviewer by spawning a Cursor subagent directly with the task-card prompt + `allowed_paths` + role; it collects the JSON+Markdown reports and runs the scope audit. No external CLI is required. See "How To Dispatch A Worker In Cursor App" in `adapters/cursor/SKILL.md`.
- Optional scripted/CI bridge: the local Cursor CLI (`agent`, legacy alias `cursor-agent`) via `run_multi_agent.py --runtime cursor`. Install only if needed: `curl https://cursor.com/install -fsS | bash` or, on native Windows, `irm 'https://cursor.com/install?win32=true' | iex`; the tmux-based bridge also needs `bash` + `tmux` (use WSL on native Windows).
- Other paths: user-driven `/multitask` (Cursor 3 App), and programmatic headless/SDK via `adapters/cursor/scripts/prepare_cursor_sdk.py` → `agent -p --output-format json|stream-json` or `@cursor/sdk` (`adapters/cursor/sdk/run_workers.mjs`, local/cloud/self-hosted). See `adapters/cursor/SDK.md`. All paths enforce the same task-card + dual result-report contract; Main still owns gate sync + scope audit.
- Run `scripts/doctor.py --client cursor` for a friendly readiness report with Chinese remediation hints.
- Manual prompt fallback: `--runtime cursor-desktop` only when neither delegation nor the Cursor CLI is available.

### Claude Code

- Install `claude-code-multi-agent-pack-v0.3.1.zip` or run `scripts/install_native_skills.py --client claude` from the repo.
- Native skill dirs: `~/.claude/skills/claude-code-multi-agent`, `~/.agents/skills/claude-code-multi-agent`.
- Native subagents: `~/.claude/agents/multi-agent-worker.md`, `multi-agent-reviewer.md`, `multi-agent-verifier.md`.
- CLI bridge: `scripts/run_multi_agent.py --runtime claude-code --task-card ...`.
- OpenClaw ACP: add `--mode acp`.

### OpenClaw

- Install `adapters/openclaw/` as skill `openclaw-multi-agent`.
- Full session workflow is documented in `adapters/openclaw/QUICKSTART.md`.
- Other adapters delegate here for scripts, templates, gates, and audits.

### Hermes

- Install `hermes-multi-agent-pack-v0.3.1.zip` or run `scripts/install_native_skills.py --client hermes` from the repo.
- Native skill dirs (agentskills.io standard): `~/.agents/skills/hermes-multi-agent`, `~/.hermes/skills/hermes-multi-agent`.
- App/CLI full mode: a Hermes Agent loads the portable `SKILL.md` natively and orchestrates Workers through its native MCP tools plus the bundled OpenClaw mission-control scripts (`create_task_cards.py`, `update_task_status.py`, `audit_worker_output.py`, `memory_log.py`). This adapter does not duplicate gate logic.
- MCP wiring: register the coordinator under `mcp_servers` in `~/.hermes/config.yaml` (stdio or http) — `scripts/configure_mcp.py --client hermes` prints a paste-ready block. Hermes connects every `mcp_servers` entry at startup and injects their tools as native tools.
- Worker launch: `scripts/run_multi_agent.py --runtime hermes` prints the MCP / handoff guidance (it does not spawn a process).
- Persistent memory: append run outcomes to `MEMORY.md` (append-only, secret-free); recall feeds the next run's task-card `context` but never substitutes for a passing `scope_audit`.
- Self-check: `python3 adapters/hermes/scripts/hermes_self_check.py --self-check`.

### VS Code

- Use workspace instructions and MCP client configuration.
- Use the IDE panel scaffold for `.codex-multi-agent/` visibility when useful.

## Verifier-gated loop (run_loop.py)

Any client can wrap a Worker in a bounded, self-correcting loop with
`adapters/openclaw/scripts/run_loop.py`. It encodes the loop-engineering
contract: an explicit verifiable **Goal**, a **maker** that performs one Worker
round, an **independent verifier** (the producer may not grade itself, so
`maker != checker` is enforced), **repair** feedback threaded into the next
round, per-round **memory**, and a hard `--max-iterations` / budget bound (loops
are never unbounded).

In real mode the maker dispatches one Worker via `scripts/run_multi_agent.py`
and the verifier runs `--verify-command` (returncode 0 = passed); add
`--with-audit` to AND it with `audit_worker_output.py`'s `ok`, so a round only
"passes" when both the verify command and the scope audit gate are green.

```bash
python3 adapters/openclaw/scripts/run_loop.py --self-check   # deterministic, no repo/CLI touch
python3 adapters/openclaw/scripts/run_loop.py \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --runtime openclaw --verify-command "pytest -q" \
  --with-audit --max-iterations 5 --state-dir .codex-multi-agent
```

This does not replace Main's accountability: Main still owns gate sync, scope
audit, and final delivery.

## Dependency readiness (auto-unblock)

`create_task_cards.py` records the dependency graph on each `ownership.json`
task, and `update_task_status.py --sync` derives `dependencies` / `blocked_by` /
`ready_to_spawn` per task in `status.json` (advisory only — gate pass/fail is
unchanged). Main / loops can pick the next unblocked task with:

```bash
python3 adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --ready
```

To drive the whole graph in dependency order, `run_graph.py` repeatedly dispatches
ready tasks until the graph completes / deadlocks (bounded by `--max-rounds`; dry
plan by default, `--execute` to launch):

```bash
python3 adapters/openclaw/scripts/run_graph.py --state-dir .codex-multi-agent            # dry plan
python3 adapters/openclaw/scripts/run_graph.py --state-dir .codex-multi-agent --execute  # dispatch
```

Over MCP the same readiness is reachable from the `multi-agent://state` resource.

## Portable State

```text
.codex-multi-agent/
  tasks/       # task cards
  results/     # JSON + Markdown result reports
  status.json  # gates
  ownership.json
  audits/
```

Do not commit `.codex-multi-agent/` unless the user explicitly asks.
