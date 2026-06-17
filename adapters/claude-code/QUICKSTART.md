# Claude Code Multi-Agent Quickstart

Dependency-free Python 3. Reuses OpenClaw mission-control scripts.

## 0. Install Native Skill And Agents

From the extracted Claude package root:

```bash
python3 scripts/install_native_skills.py --client claude --scope primary --force
python3 scripts/install_native_skills.py --client claude --check
```

Reload Claude Code. Then ask:

```text
Use claude-code-multi-agent. Split this task into scoped task cards, delegate Workers and Reviewers to bundled subagents, collect result reports, and audit the diff before final delivery.
```

## 1. Generate Task Cards

```bash
cd /path/to/target-repo
python3 /path/to/claude-code-multi-agent/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/claude-code-multi-agent/adapters/claude-code/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

## 2a. Full Mode: Native Claude Subagents

Use the bundled subagents installed under `~/.claude/agents`:

- `multi-agent-worker` for scoped writes
- `multi-agent-reviewer` for read-only review
- `multi-agent-verifier` for validation evidence

Each subagent must write the result reports listed in its task card.

## 2b. CLI Bridge

```bash
python3 /path/to/claude-code-multi-agent/scripts/run_multi_agent.py \
  --runtime claude-code \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Quota warning: local `claude --print` is subject to account budget / 429 errors. The launcher exits non-zero with `quota_exhausted` when detected.

## 2c. OpenClaw ACP Handoff

```bash
python3 /path/to/claude-code-multi-agent/scripts/run_multi_agent.py \
  --runtime claude-code \
  --mode acp \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

## 2d. Manual Fallback

Use only when native subagents and CLI bridge are unavailable:

```bash
python3 /path/to/claude-code-multi-agent/scripts/run_multi_agent.py \
  --runtime claude-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

## 3. Gates And Audit

Follow [OpenClaw QUICKSTART](../openclaw/QUICKSTART.md) gate sync and audit steps.

## Self-check

```bash
python3 /path/to/claude-code-multi-agent/scripts/install_native_skills.py --client claude --check
python3 /path/to/claude-code-multi-agent/adapters/claude-code/scripts/claude_code_self_check.py
```
