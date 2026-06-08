---
name: multi-agent-coding
description: Prompt-guided multi-agent coordination for coding tasks across Codex, Cursor, Claude Code, OpenClaw, Hermes, and VS Code. Use when an agent client should coordinate multiple specialist agents or role-based passes for complex software work, including multi-module research, scoped implementation, parallel review, bug investigation, refactoring, verification, or when the user asks to use multiple agents, subagents, workers, reviewers, planners, parallel agents, or skills such as review skills across multiple agents. Also use to define task cards, allowed paths, client adapters, MCP-backed state, reviewer-only workflows, skill-use permissions, and final integration rules.
---

# multi-agent-coding

Use this skill to coordinate coding work with controlled specialist roles. This is a prompt-guided coordination protocol, not a sandbox, orchestrator, or permission enforcement system. The main agent remains responsible for planning, delegation, integration, verification, and final delivery.

## Core Rules

- Treat this skill as process guidance, not security isolation.
- Use the smallest effective agent set; do not spawn agents for trivial work.
- Keep the main agent accountable for all subagent outputs and code changes.
- Define `allowed_paths`, `blocked_commands`, validation requirements, and stop conditions before any scoped Worker starts.
- Keep Explorer and Reviewer roles read-only.
- Require Worker outputs to return to the main agent for diff audit before final delivery.
- Do not store secrets, tokens, credential values, or large private code excerpts in task reports.

## Cross-Client Support

Support Codex, Cursor, Claude Code, OpenClaw, Hermes, and VS Code by keeping the shared protocol independent of any one client runtime. Treat task cards, result reports, role permissions, skill-use approvals, review findings, scope audits, and final delivery format as the portable contract.

If the user asks to install this skill from GitHub, read `docs/agent-install.md` first and choose the client-specific package. Use `codex-multi-agent-skill-*` for Codex, `cursor-multi-agent-pack-*` for Cursor, `claude-code-multi-agent-pack-*` for Claude Code, and `openclaw-multi-agent-skill-*` for OpenClaw/Her. The generic `multi-agent-coding-skill-*` package is protocol guidance only.

Use client-specific adapters for execution details:

- Codex: use this folder as a Codex skill and use native subagents when available.
- Cursor: translate core rules into project rules and use MCP for state if configured.
- Claude Code: translate core rules into `CLAUDE.md`/commands and use MCP tools when configured.
- OpenClaw: install `adapters/openclaw/` as the standalone skill `openclaw-multi-agent`; map roles to `sessions_spawn`, `sessions_send`, and `sessions_yield`; use the bundled scripts for task cards and scope audit.
- Hermes: use the protocol as a task-card and role-routing contract; prefer MCP for state.
- VS Code: use workspace instructions plus MCP/client extensions where available.

When MCP is available, use it for task state, approvals, findings, and audits. When MCP is unavailable, fall back to the bundled templates and checklists.
## Trigger Handling

If the user explicitly asks for multiple agents, parallel agents, subagents, workers, reviewers, planners, or multi-agent review, enter this skill. If the task is small, use the Quick Path and explain that additional agents are unnecessary.

If the user asks for multiple agents to review something, use Review Mode. Create Reviewer agents, not write-capable Workers. If a review skill such as `ssrd` is available or named by the user, authorize it in each Reviewer task card with `may_use_skills: [ssrd]` and `write_permission: false`.

## Default Paths

Use Quick Path for simple work:

1. Intake.
2. Plan Lite.
3. Implement or answer.
4. Review Lite.
5. Verify if useful.
6. Deliver.

Use Multi-Agent Path for complex work:

1. Intake and environment check.
2. Task graph and ownership plan.
3. Explorer fan-out when research is needed.
4. Synthesize findings.
5. Scoped Worker execution only when paths are clear.
6. Main-agent diff audit.
7. Reviewer pass.
8. Verification.
9. Final delivery.

## Roles

### Main Agent

Coordinate the task, decide whether multi-agent work is justified, write task cards, review outputs, audit diffs, resolve conflicts, run or request verification, and deliver the final result.

### Explorer

Read-only. Investigate code, architecture, tests, requirements, or failure modes. Report facts, evidence, relevant files, risks, and recommended next steps. Do not edit files, spawn subagents, or make final decisions.

### Worker

Scoped write. Implement only within `allowed_paths` and allowed commands. Use only authorized skills. Stop and report a blocker if the task requires scope expansion, secret access, dependency installation, deployment, destructive commands, or unclear test failures.

### Reviewer

Read-only. Review plans, diffs, code, documents, or designs. Use authorized review skills such as `ssrd` when the task card allows them. Report findings by severity with evidence. Do not edit files or spawn subagents.

### Verifier

Run or describe validation using allowed test, lint, build, or reproduction commands. Do not modify code unless explicitly assigned a Worker task card.

### Integrator

Usually the main agent. Merge results, resolve inconsistencies, enforce ownership boundaries, apply reviewer feedback, and prepare final delivery.

## Permission Matrix

| Role | Read code | Write files | Shell | Network | Git write | Spawn subagents | Use skills |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Explorer | Yes | No | Read-only | No unless authorized | No | No | Read-only skills |
| Reviewer | Yes | No | Read-only | No unless authorized | No | No | Review skills only |
| Worker | Yes | `allowed_paths` only | Limited allowed commands | No unless authorized | No unless authorized | No by default | Task-card skills only |
| Verifier | Yes | No by default | Test/build commands only | No unless authorized | No | No | Testing skills |
| Main | Yes | Yes, respecting user changes | Environment-dependent | Environment-dependent | User-gated | Yes | Yes |

## Worker Skill Use

A Worker may use another skill only when all conditions hold:

- The skill is listed in `may_use_skills` or the main agent explicitly approves it.
- The skill directly supports the Worker objective.
- The skill does not expand file, command, network, credential, git, or role permissions.
- All outputs stay within `allowed_paths`.
- The skill does not require blocked commands or forbidden paths.

If any condition fails, the Worker must stop and return a Skill Use Request instead of using the skill.

Use this request format:

```text
Skill Use Request
Requested Skill:
Reason:
Scope:
Risk:
Requested Permission:
```

## Subagent Rules

Only the main agent may spawn subagents by default. A Worker may spawn a subagent only if its task card says `may_spawn_subagents: true`. Worker subagents must normally be read-only Explorers. Do not let a Worker spawn another Worker or Reviewer. Worker subagents inherit the Worker's scope and cannot expand it.

## Safety Rules

Do not read, copy, summarize, or store secret values. Do not actively grep/token-hunt for secrets. If a search accidentally reveals a likely secret, report only the file path and risk, not the value.

Treat these as forbidden unless the user explicitly authorizes access and the task requires it:

- `.env`, `.env.*`, `.npmrc`, `.pypirc`, `.netrc`
- `*.pem`, `*.key`, `*.p12`, `*.pfx`, private certificates
- `id_rsa`, `id_ed25519`, `~/.ssh/**`
- `~/.codex/auth.json`, browser profiles, browser cookies
- cloud credentials, kubeconfig, service account JSON, CI secret dumps

Block these commands for Workers by default:

- dependency installation unless authorized
- deploy, publish, release, or production migration
- `git push`, `git reset --hard`, rebase, force-push
- destructive deletion or global config mutation
- credential sync or token export

## Workspace Hygiene

Create `.codex-multi-agent/` only for larger tasks that need persistent coordination. Default it to local-only and do not commit it unless the user explicitly wants that. Store summaries, paths, decisions, and task status; do not store secrets or long proprietary code excerpts.

Before modifying files, inspect dirty worktree state when available. Do not overwrite user changes. If unexpected changes appear, stop and ask the user how to proceed.

## Conflict Handling

The main agent must audit worker results before final delivery:

- Check whether any Worker touched paths outside `allowed_paths`.
- Check whether Workers modified overlapping files.
- Separate user pre-existing changes from agent changes.
- Stop on ownership conflicts, unexplained test failures, or required scope expansion.
- Re-plan or ask the user instead of silently merging risky changes.

## Mode Defaults

- `research`: Main + 1-3 Explorers, no writes, final research report.
- `implement`: Main + optional Explorers + 1-2 Workers + Reviewer + Verifier.
- `fix`: Main + Explorer + usually one Worker + Verifier; avoid parallel Workers until root cause is clear.
- `review`: Main + one or more Reviewers, no writes; use review skills such as `ssrd` when authorized.
- `refactor`: Main + impact Explorer + small-batch Workers + Reviewer + Verifier.

## Final Delivery

Include changed files, validation run, validation not run, review findings handled, residual risks, and concise follow-up options when relevant.

## Client Adapters

For OpenClaw/Her, use the standalone adapter instead of loading the whole repo:

- `adapters/openclaw/SKILL.md`
- `adapters/openclaw/README.md`
- `adapters/openclaw/scripts/create_task_cards.py`
- `adapters/openclaw/scripts/audit_worker_output.py`

## Bundled Resources

Load only the resource needed for the current step:

- `checklists/should-use-multi-agent.md` to decide Quick Path vs Multi-Agent Path.
- `checklists/environment-check.md` before multi-agent work.
- `checklists/permission-matrix.md` when writing task cards.
- `checklists/diff-audit.md` before integration/final delivery.
- `checklists/safety.md` for sensitive files and blocked operations.
- `templates/task-card.md` to delegate work.
- `templates/result-report.md` to collect subagent output.
- `templates/final-delivery.md` for final responses.
- `examples/feature.md`, `examples/bugfix.md`, and `examples/review.md` for common flows.
