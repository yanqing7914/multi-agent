# OpenClaw Multi-Agent Adapter

This adapter is the OpenClaw/Her-specific version of `multi-agent-coding`.

It removes broad cross-client guidance and focuses on practical OpenClaw session workflows:

- `sessions_spawn` / `sessions_send` style delegation.
- ACP or native subagent runtime selection.
- Scoped Worker task cards.
- Read-only Reviewer sessions, including `ssrd` review.
- Script-assisted task-card generation and worker output audit.

## When to use

Use this adapter for complex multi-role coding tasks:

- multi-module feature work
- large codebase research
- multi-agent review
- SSRD/security review
- complex bug investigation
- refactor with scoped module ownership

Do not use this adapter for:

- simple coding tasks
- explicit single-agent tasks
- direct Claude/Codex routing handled by `acp-router`
- batch homogeneous jobs handled by `parallel-claude`

## Files

```text
SKILL.md
scripts/create_task_cards.py
scripts/audit_worker_output.py
templates/task-card.md
templates/result-report.md
templates/ownership.example.json
examples/favorite-feature.yaml
```

## Basic workflow

```text
Main session
  -> create task cards
  -> sessions_spawn Explorer/Worker/Reviewer
  -> sessions_send task cards
  -> collect result reports
  -> audit worker output
  -> run review/verify
  -> final delivery
```

## Script examples

Create task cards:

```bash
python scripts/create_task_cards.py --task "Add vehicle favorite feature" --mode implement --modules backend frontend tests --out .codex-multi-agent/tasks
```

Audit Worker results:

```bash
python scripts/audit_worker_output.py --ownership .codex-multi-agent/ownership.json --results .codex-multi-agent/results --changed-files .codex-multi-agent/changed-files.txt
```
