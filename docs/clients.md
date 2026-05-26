# Client Support Model

This project targets a shared multi-agent coordination protocol across **Codex**, **Cursor**, **Claude Code**, **OpenClaw**, Hermes, and VS Code.

**v1 status:** Thin adapters exist for OpenClaw, Cursor, Codex, and Claude Code under `adapters/`. They reuse the OpenClaw mission-control scripts and `.codex-multi-agent/` contract. Hermes and VS Code remain documentation-only.

## Support layers

| Layer | Purpose | Required everywhere |
| --- | --- | --- |
| Skill / rule layer | Human-readable coordination workflow, roles, task cards, review rules | Yes |
| MCP coordination layer | Shared task state, findings, approvals, and scope checks | Recommended (v2) |
| Client adapter layer | Maps each client to prompts, launchers, and handoffs | Yes |
| Execution layer | Actual code edits, tests, shell commands, and agent spawning | Client-specific |

## Compatibility principle

The portable contract is not the UI or agent runtime. The portable contract is:

- Task cards
- Result reports (JSON + Markdown)
- Role names and permissions
- Skill-use approvals
- Review findings
- Scope and diff audit records
- Final delivery format

Each client may implement spawning, permissions, and tool calls differently.

## v1 adapter matrix

| Client | Adapter path | Worker launch | Mission-control scripts | Status |
| --- | --- | --- | --- | --- |
| OpenClaw | `adapters/openclaw/` | `sessions_spawn` / `sessions_send` / `sessions_yield` | Local (canonical) | **v1 in** |
| Cursor | `adapters/cursor/` | `launch_cursor_worker.sh` → `agent` via tmux | Reuses OpenClaw scripts | **v1 in** |
| Codex | `adapters/codex/` | `launch_codex_worker.sh` → `codex exec` | Reuses OpenClaw scripts | **v1 in** |
| Claude Code | `adapters/claude-code/` | ACP handoff **or** `claude --print` | Reuses OpenClaw scripts | **v1 in** |
| Hermes | (planned) | External runtime | MCP recommended | docs only |
| VS Code | (planned) | Chat / MCP client | MCP recommended | docs only |

**Cross-adapter entrypoint:** `scripts/run_multi_agent.py --runtime <name> --task-card <path>`

**Validation:** `scripts/validate_all_adapters.py` (OpenClaw `validate_all.py` + per-adapter self-checks)

## Adapter layout (actual)

```text
adapters/
  openclaw/          # canonical mission-control scripts + OpenClaw session mapping
  cursor/            # SKILL.md + launch_cursor_worker.sh + examples
  codex/             # SKILL.md + launch_codex_worker.sh + examples
  claude-code/       # SKILL.md + launch_claude_worker.sh + ACP/local paths
  _shared/           # bridge.py, self_check.py (thin helpers, no fork)
scripts/
  run_multi_agent.py
  validate_all_adapters.py
```

Source of truth remains root `SKILL.md`, `templates/`, `checklists/`, `examples/`, and `docs/mcp-format.md`.

## Behavior by client

### Codex

- Install root skill + `adapters/codex/SKILL.md`.
- Generate cards with `adapters/openclaw/scripts/create_task_cards.py`.
- Launch workers: `scripts/run_multi_agent.py --runtime codex --task-card ...`
- Use git worktrees for parallel Workers (see `adapters/codex/README.md`).
- MCP optional (v2).

### Cursor

- Use `adapters/cursor/SKILL.md` and project rules from root `SKILL.md`.
- Main runs OpenClaw scripts for state; workers via `launch_cursor_worker.sh`.
- Requires Cursor `agent` CLI + tmux for detached workers.
- MCP optional (v2).

### Claude Code

- **Inside OpenClaw:** `runtime=acp` + task card handoff (preferred).
- **Standalone:** `launch_claude_worker.sh` or `run_multi_agent.py --runtime claude-code`.
- Same preflight and result-report gates as OpenClaw v1.

### OpenClaw

- Install `adapters/openclaw/` as skill `openclaw-multi-agent`.
- Full session workflow documented in `adapters/openclaw/QUICKSTART.md`.
- Other adapters delegate here for scripts and templates.

### Hermes

- Use the protocol as a role-routing and task-card contract.
- Prefer MCP for state (v2), because Hermes runtime details may vary.

### VS Code

- Use workspace instructions and MCP client configuration (v2/v3).
- Use Review Mode for multi-perspective diff reviews.

## Portable state (v1)

```text
.codex-multi-agent/
  tasks/       # task cards (portable)
  results/     # JSON + Markdown result reports
  status.json  # gates (Main reads; scripts update)
  ownership.json
  audits/
```

Do not commit `.codex-multi-agent/` unless the user explicitly asks.
