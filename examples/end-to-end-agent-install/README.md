# End-to-End: GitHub Link To Multi-Agent Run

This demo shows the original product goal:

> A user sends `https://github.com/yanqing7914/multi-agent` to their agent and
> says "install this multi-agent skill", then the agent chooses the right client
> package and runs a scoped multi-agent workflow.

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
   - Codex Desktop -> `codex-multi-agent-skill-v0.1.5.zip`
   - Cursor Desktop -> `cursor-multi-agent-pack-v0.1.5.zip`
   - Claude Desktop / Claude Code -> `claude-code-multi-agent-pack-v0.1.5.zip`
   - OpenClaw / Her -> `openclaw-multi-agent-skill-v0.1.5.zip`
4. Install or unpack the package into the client-specific location.
5. Generate `.codex-multi-agent/` task cards in the target repo.
6. Start the right execution path:
   - Codex Desktop: native subagent first (`--runtime codex-native`)
   - Cursor Desktop: prompt/rules path (`--runtime cursor-desktop`)
   - Claude Desktop / Claude.ai: custom-skill prompt path (`--runtime claude-desktop`)
   - CLI fallback: `--runtime codex`, `--runtime cursor`, or `--runtime claude-code`
7. Require every Worker/Reviewer/Verifier to write JSON and Markdown result reports.
8. Run gate sync and scope audit before final delivery.

## Minimal Commands

After installation, from the target repo:

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
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
# Codex Desktop native subagent prompt
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex-native \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md

# Cursor Desktop Agent prompt
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime cursor-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md

# Claude Desktop / Claude.ai prompt
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime claude-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Finally:

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync

git diff --name-only > .codex-multi-agent/changed-files.txt
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

## What This Proves

- The GitHub link is enough for an agent to find installation instructions.
- Client packages are split by actual runtime needs, not a one-size-fits-all zip.
- Desktop users have a usable path even without CLI auto-workers.
- The Main agent remains accountable for result reports, diff audit, and final delivery.

## Current Gaps

- Cursor Desktop and Claude Desktop paths are prompt/rules/custom-skill guided, not native subagent APIs.
- Fully automatic background execution still requires the corresponding CLI or OpenClaw/Her.
- A future IDE panel can hide most commands behind buttons.
