# Codex Multi-Agent Adapter

Thin Codex layer over [`adapters/openclaw/`](../openclaw/) mission-control
scripts.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## What This Enables

Codex Desktop users should not have to install Codex CLI just to arrange
Workers. The preferred flow is:

1. User asks Codex Desktop Main to use multiple agents.
2. Main generates scoped task cards.
3. Main uses native Codex Desktop subagent tools when available.
4. Workers/Reviewers write result reports.
5. Main runs gate sync, scope audit, and final integration.

The prompt-handoff file flow still exists, but it is a fallback for Desktop
clients that do not expose native subagent tools.

## Install

1. Install `codex-multi-agent-skill-*.zip` into the Codex skills directory.
2. Start a Codex Desktop thread in the target repository.
3. Ask for multi-agent work explicitly, for example:

```text
$codex-multi-agent
Use native Codex Desktop subagents. Spawn one Worker for backend changes and
one Reviewer using ssrd. Wait for both and audit the diff before final delivery.
```

## Usage: Codex Desktop Native Subagents

Main prepares the task-card prompt:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex-native \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Expected output:

```json
{
  "ok": true,
  "runtime": "codex-desktop",
  "mode": "native-subagent",
  "agent_type": "worker",
  "prompt_path": ".../.codex-multi-agent/native-subagents/T002-worker-backend.spawn.md",
  "may_use_skills": [],
  "spawn_instruction": {
    "agent_type": "worker",
    "message_source": ".../T002-worker-backend.spawn.md",
    "fork_context": false
  }
}
```

Then Main reads `prompt_path` and spawns a native Codex subagent with that
prompt. If `may_use_skills` contains `ssrd` or another named skill, Main should
attach that skill when the client supports structured skill input, or name it
explicitly in the subagent prompt.

## Usage: Desktop Prompt Handoff Fallback

Use this only when native subagent tools are unavailable:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

This writes `.codex-multi-agent/desktop-workers/*.prompt.md`. Open each prompt
in a new Codex Desktop session or task. The Worker writes the JSON/Markdown
reports listed in the prompt; Main then runs sync and audit.

## Usage: Codex CLI Fallback

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Direct CLI launcher:

```bash
/path/to/multi-agent-coding/adapters/codex/scripts/launch_codex_worker.sh \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Optional env / CLI overrides:

| Variable / flag | Default | Purpose |
| --- | --- | --- |
| `CODEX_MODEL` / `--model` | `gpt-5.3-codex` | Model passed to `codex exec` |
| `CODEX_BIN` / `--codex-bin` | `codex` | Codex CLI binary |
| `CODEX_SANDBOX` / `--sandbox` | `workspace-write` | Sandbox mode (`read-only`, `workspace-write`, `danger-full-access`) |

The launcher always passes `--skip-git-repo-check` and defaults to
`workspace-write` so read-only sandboxes do not silently block writes.

## Result Contract

Every subagent must write:

- JSON result report under `.codex-multi-agent/results/`
- Markdown result report under `.codex-multi-agent/results/`
- `workspace_observed`, `required_paths_verified`, `files_read`, `files_changed`, and validation evidence

Main must run OpenClaw gate sync and scope audit before final delivery.

## What Works Today

- Native Codex Desktop subagent prompt preparation
- Desktop handoff fallback for users without native spawn exposure
- CLI fallback via `codex exec`
- Preflight gate before worker execution
- Same result-report contract as OpenClaw v1
- OpenClaw gate sync / audit when Main runs shared scripts

## Limitations

- Scripts cannot call Desktop-only subagent tools by themselves; the Codex Main
  agent must use the native spawn tool when the app exposes it.
- Native subagents inherit the current sandbox and approval policy.
- Handoff fallback does not automatically create a second Desktop session.
- CLI fallback requires Codex CLI and a writable sandbox.

## Self-check

```bash
python3 adapters/codex/scripts/codex_self_check.py
```
