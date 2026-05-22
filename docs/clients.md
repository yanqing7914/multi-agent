# Client Support Model

This project targets a shared multi-agent coordination protocol that can run across Codex, Cursor, Claude Code, OpenClaw, Hermes, and VS Code.

## Support layers

| Layer | Purpose | Required everywhere |
| --- | --- | --- |
| Skill / rule layer | Human-readable coordination workflow, roles, task cards, review rules | Yes |
| MCP coordination layer | Shared task state, findings, approvals, and scope checks | Recommended |
| Client adapter layer | Maps each client to prompts, rules, commands, and MCP config | Yes |
| Execution layer | Actual code edits, tests, shell commands, and agent spawning | Client-specific |

## Compatibility principle

The portable contract is not the UI or agent runtime. The portable contract is:

- Task cards.
- Result reports.
- Role names and permissions.
- Skill-use approvals.
- Review findings.
- Scope and diff audit records.
- Final delivery format.

Each client may implement spawning, permissions, and tool calls differently.

## Client matrix

| Client | Skill/rules support | MCP support goal | Agent spawning model | Notes |
| --- | --- | --- | --- | --- |
| Codex | `SKILL.md` plus bundled templates | Use MCP for state and audit when configured | Native subagents where available, otherwise prompt-guided roles | Primary target |
| Cursor | `.cursor/rules` or project rules generated from `SKILL.md` | Use configured MCP server if Cursor supports it | Usually agent/chat tabs or manual role prompts | Needs adapter docs |
| Claude Code | `CLAUDE.md` plus slash-command style prompts | Use MCP server configuration | Task/subagent features when available, otherwise prompt-guided roles | Strong candidate for MCP-backed state |
| OpenClaw | `SKILL.md` style skill package | Use MCP if available; otherwise OpenClaw sessions/state | Sessions-based multi-agent workflows | Maps well to Reviewer/Worker task cards |
| Hermes | Adapter prompt/rules file | MCP-backed state is the recommended portable layer | Depends on Hermes runtime | Treat as external agent client |
| VS Code | Workspace docs plus assistant rules | Use MCP extension/client where available | Usually chat participants or manual roles | Good for local state and review workflows |

## Adapter outputs

Adapters should generate or maintain these client-specific files:

```text
adapters/
  codex/SKILL.md
  cursor/rules.md
  claude/CLAUDE.md
  openclaw/SKILL.md
  hermes/rules.md
  vscode/instructions.md
```

The source of truth should remain the shared protocol in `SKILL.md`, `templates/`, `checklists/`, `examples/`, and `docs/mcp-format.md`.

## Behavior by client

### Codex

- Use this repo as a Codex skill.
- Use `templates/task-card.md` before delegating to subagents.
- Use `checklists/diff-audit.md` before final delivery.
- Use MCP tools for task state when available.

### Cursor

- Convert the core rules into Cursor project rules.
- Treat Workers as scoped agent tasks or chat prompts.
- Use the MCP server for task registry, review findings, and skill-use approvals if configured.

### Claude Code

- Convert core rules into `CLAUDE.md` or command prompts.
- Use MCP tools for task state and review finding storage.
- Keep Reviewer roles read-only and Worker roles path-scoped.

### OpenClaw

- Package as an OpenClaw-compatible skill.
- Map Explorer/Worker/Reviewer roles to OpenClaw sessions.
- Use session messages for task cards and result reports.

### Hermes

- Use the protocol as a role-routing and task-card contract.
- Prefer MCP for state, because Hermes runtime details may vary.
- Keep execution privileges client-specific and explicit.

### VS Code

- Use workspace instructions and MCP client configuration.
- Use Review Mode for multi-perspective diff reviews.
- Keep `.codex-multi-agent/` local-only unless the user chooses otherwise.