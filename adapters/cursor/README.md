# Cursor Multi-Agent Adapter

Thin Cursor layer over [`adapters/openclaw/`](../openclaw/) mission-control scripts. It does not duplicate task-card generation, gate sync, or audit logic.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## What This Enables

Cursor App and Cursor CLI both get a native Agent Skill for the same workflow:

1. Cursor Main receives a multi-agent request.
2. Main generates scoped task cards under `.codex-multi-agent/`.
3. Main launches Workers/Reviewers through the local `agent` CLI bridge when automation is required.
4. Each agent writes JSON + Markdown result reports.
5. Main runs gate sync, scope audit, and final delivery.

Cursor App currently does not expose a public Codex/Claude-style native subagent API. That is why v0.2.0 treats the `agent` CLI bridge as the full automation path for Cursor App and CLI. Manual prompt handoff still exists, but it is a fallback.

## Install

From the extracted `cursor-multi-agent-pack-v0.2.0.zip` root:

```bash
python3 scripts/install_native_skills.py --client cursor --scope primary --force
python3 scripts/install_native_skills.py --client cursor --check
```

The installer writes native skill files to:

```text
~/.agents/skills/cursor-multi-agent
~/.cursor/skills/cursor-multi-agent
```

For workspace-level rules, keep or copy the bundled `.cursor/rules/multi-agent-coding.mdc`.

## Usage: Cursor App Full Mode

After the skill is installed and Cursor is reloaded, ask Cursor Agent:

```text
Use cursor-multi-agent. Split this change into scoped task cards, launch Workers through the local agent CLI bridge, collect result reports, run review and scope audit, then deliver only after gates pass.
```

For each task card:

```bash
python3 /path/to/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

The bridge spawns or runs Cursor `agent -p` with the task-card prompt and result-report contract. Main must still collect reports and run audit.

## Manual Fallback

Use only if `agent` CLI is unavailable or the user explicitly wants manual handoff:

```bash
python3 /path/to/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

This writes `.codex-multi-agent/cursor-desktop/*.cursor.md`. Open or paste the prompt into Cursor Agent in the target workspace.

## Contract

| Artifact | Location |
| --- | --- |
| Task cards | `.codex-multi-agent/tasks/*.md` |
| Result Markdown | `.codex-multi-agent/results/*.md` |
| Result JSON | `.codex-multi-agent/results/*.json` |
| Manual prompts | `.codex-multi-agent/cursor-desktop/*.cursor.md` |
| Preflight | `adapters/openclaw/scripts/verify_workspace.py` |
| Schema | `adapters/openclaw/templates/result-report.md` |

## What Works Today

- Native Cursor Agent Skill install for App and CLI
- Cursor rules pack via `.cursor/rules/multi-agent-coding.mdc`
- Automatic Worker bridge through local Cursor `agent` CLI
- Foreground debug mode and tmux-detached mode
- Prompt fallback for machines without `agent`
- Shared gate/audit path via OpenClaw scripts

## Readiness

- `native_skill_ready=true`: Cursor can load the skill.
- `complete_worker_bridge_ready=true`: Cursor `agent` CLI is present, so automatic Workers can run.
- If bridge readiness is false, do not claim full automation; use manual fallback or install Cursor CLI.

## Self-check

```bash
python3 scripts/install_native_skills.py --client cursor --check
python3 adapters/cursor/scripts/cursor_self_check.py
```
