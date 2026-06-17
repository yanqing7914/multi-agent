# Client Support Model

This project targets a shared multi-agent coordination protocol across **Codex**, **Cursor**, **Claude Code**, **OpenClaw**, Hermes, and VS Code.

**v0.2 status:** Codex, Cursor, and Claude Code now have client-native skill packages. Codex and Claude Code include native subagent definitions. Cursor uses native Agent Skills plus the local `agent` CLI bridge for complete Worker automation. OpenClaw/Her remains the canonical mission-control reference implementation.

## Support layers

| Layer | Purpose | Required everywhere |
| --- | --- | --- |
| Native skill layer | Client-discoverable instructions and trigger metadata | Yes for Codex/Cursor/Claude/OpenClaw |
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
| Cursor | `cursor-multi-agent` | Native Agent Skill + local `agent` CLI bridge | `agent -p` bridge | `cursor` | **v0.2 in, bridge required** |
| Claude Code | `claude-code-multi-agent` | Native skill + bundled `.claude/agents` | Native subagents or `claude --print` bridge | `claude-code` | **v0.2 in** |
| OpenClaw / Her | `openclaw-multi-agent` | `sessions_spawn` / `sessions_send` / `sessions_yield` | Runtime-specific | `openclaw` / ACP | **v1 canonical** |
| Hermes | Protocol package | Runtime-specific | Runtime-specific | MCP recommended | docs only |
| VS Code | Protocol + panel | Extension/MCP dependent | CLI dependent | MCP/panel planned | scaffold |

**Cross-adapter entrypoint:** `scripts/run_multi_agent.py --runtime <name> --task-card <path>`.

**Validation:** `scripts/validate_all_adapters.py` runs OpenClaw checks, client checks, and native installer self-check.

## Adapter Layout

```text
adapters/
  openclaw/          # canonical mission-control scripts + OpenClaw session mapping
  cursor/            # native Cursor skill + agent CLI bridge + rules
  codex/             # native Codex skill + custom agents + codex exec bridge
  claude-code/       # native Claude skill + subagents + claude bridge / ACP
  _shared/           # bridge.py, self_check.py
scripts/
  install_native_skills.py
  run_multi_agent.py
  validate_all_adapters.py
```

Source of truth remains root `SKILL.md`, `templates/`, `checklists/`, `examples/`, and `docs/mcp-format.md`.

## Behavior By Client

### Codex

- Install `codex-multi-agent-skill-v0.2.0.zip` or run `scripts/install_native_skills.py --client codex` from the repo.
- Native skill dirs: `~/.agents/skills/codex-multi-agent`, `~/.codex/skills/codex-multi-agent`.
- Native custom agents: `~/.codex/agents/multi-agent-worker.toml`, `~/.codex/agents/multi-agent-reviewer.toml`.
- App full mode: Main uses native subagents after the user asks for multi-agent work.
- CLI bridge: `scripts/run_multi_agent.py --runtime codex --task-card ...`.

### Cursor

- Install `cursor-multi-agent-pack-v0.2.0.zip` or run `scripts/install_native_skills.py --client cursor` from the repo.
- Native skill dirs: `~/.agents/skills/cursor-multi-agent`, `~/.cursor/skills/cursor-multi-agent`.
- App and CLI full automation require local `agent` CLI for Worker launch.
- Manual prompt fallback: `--runtime cursor-desktop` only when `agent` is unavailable or explicitly requested.

### Claude Code

- Install `claude-code-multi-agent-pack-v0.2.0.zip` or run `scripts/install_native_skills.py --client claude` from the repo.
- Native skill dirs: `~/.claude/skills/claude-code-multi-agent`, `~/.agents/skills/claude-code-multi-agent`.
- Native subagents: `~/.claude/agents/multi-agent-worker.md`, `multi-agent-reviewer.md`, `multi-agent-verifier.md`.
- CLI bridge: `scripts/run_multi_agent.py --runtime claude-code --task-card ...`.
- OpenClaw ACP: add `--mode acp`.

### OpenClaw

- Install `adapters/openclaw/` as skill `openclaw-multi-agent`.
- Full session workflow is documented in `adapters/openclaw/QUICKSTART.md`.
- Other adapters delegate here for scripts, templates, gates, and audits.

### Hermes

- Use the protocol as a role-routing and task-card contract.
- Prefer MCP for state because Hermes runtime details may vary.

### VS Code

- Use workspace instructions and MCP client configuration.
- Use the IDE panel scaffold for `.codex-multi-agent/` visibility when useful.

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
