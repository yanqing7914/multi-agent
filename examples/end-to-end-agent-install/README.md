# End-to-End: GitHub Link To Multi-Agent Run

This demo shows the product goal:

> A user sends `https://github.com/yanqing7914/multi-agent` to their agent and says "install this multi-agent skill". The agent chooses the right client package, installs it into the native skill directory, checks readiness, and runs a scoped multi-agent workflow.

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
3. Detect the client surface:
   - Codex App / CLI -> `codex-multi-agent-skill-v0.2.0.zip`
   - Cursor App / CLI -> `cursor-multi-agent-pack-v0.2.0.zip`
   - Claude Code App / IDE / CLI -> `claude-code-multi-agent-pack-v0.2.0.zip`
   - OpenClaw / Her -> `openclaw-multi-agent-skill-v0.2.0.zip`
4. Run the client package installer:

```bash
python3 scripts/install_native_skills.py --client all --scope primary --force
python3 scripts/install_native_skills.py --client all --check
```

5. Generate `.codex-multi-agent/` task cards in the target repo.
6. Start the right full-mode execution path:
   - Codex App/CLI: native subagents first (`--runtime codex-native`), optional `--runtime codex` bridge
   - Cursor App/CLI: native skill plus `agent` CLI bridge (`--runtime cursor`)
   - Claude Code App/CLI: bundled subagents first, optional `--runtime claude-code` bridge
   - OpenClaw/Her: session workflow / ACP handoff
7. Require every Worker/Reviewer/Verifier to write JSON and Markdown result reports.
8. Run gate sync and scope audit before final delivery.

## Minimal Commands

After installation, from the target repo:

```bash
python3 /path/to/client-pack/adapters/openclaw/scripts/create_task_cards.py \
  --task "Implement and review a small feature" \
  --mode implement \
  --modules backend tests \
  --reviewers correctness security \
  --review-skill ssrd \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

Then choose the surface:

```bash
# Codex native subagent prompt
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex-native \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md

# Cursor automatic Worker bridge
python3 /path/to/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md

# Claude Code CLI bridge, when not using native Claude subagents
python3 /path/to/claude-code-multi-agent/scripts/run_multi_agent.py \
  --runtime claude-code \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Finally:

```bash
python3 /path/to/client-pack/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync

git diff --name-only > .codex-multi-agent/changed-files.txt
python3 /path/to/client-pack/adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

## What This Proves

- A GitHub link is enough for an agent to find installation instructions.
- Client packages install into native skill locations.
- Codex App/CLI, Cursor App/CLI, and Claude Code App/CLI all share the same task-card contract.
- Cursor is honest about its bridge requirement: no local `agent`, no full automatic Worker launch.
- Main remains accountable for result reports, diff audit, and final delivery.
