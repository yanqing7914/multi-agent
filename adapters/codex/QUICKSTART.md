# Codex Multi-Agent Quickstart

Dependency-free Python 3. Reuses OpenClaw mission-control scripts.

## 0. User Prompt In Codex Desktop

Use an explicit delegation prompt. Codex only spawns subagents when the user
asks for subagents or parallel agent work.

```text
$codex-multi-agent
Use native Codex Desktop subagents for this task. Split work by module, spawn
scoped Workers, use ssrd for read-only review if available, wait for results,
then audit the diff before final delivery.
```

## 1. Generate Task Cards

```bash
cd /path/to/target-repo
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/multi-agent-coding/adapters/codex/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

## 2. Sync Gates

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync
```

## 3a. Prefer Native Codex Desktop Subagents

Prepare one spawn prompt per task card:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex-native \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Main reads the returned `prompt_path`, then spawns a native Codex subagent with
the returned `agent_type` and prompt contents.

Role mapping:

| Task role | Native agent type |
| --- | --- |
| Explorer | `explorer` |
| Reviewer | `explorer` |
| Verifier | `explorer` |
| Worker | `worker` |

If the task card lists `may_use_skills: [ssrd]`, Main attaches or names `ssrd`
for that subagent. If `ssrd` is unavailable, the subagent must report blocked.

## 3b. Fallback: Desktop Prompt Handoff

Use this only when native subagent tools are unavailable:

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Open the returned `prompt_path` in a new Codex Desktop session or task. The
Worker must write both result reports before claiming completion.

## 3c. Fallback: Codex CLI Worker

Ensure Codex CLI is authenticated in the user environment.

```bash
export CODEX_SANDBOX=workspace-write
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime codex \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Overrides: `CODEX_MODEL`, `CODEX_BIN`, `CODEX_SANDBOX`, or launcher flags.

## 4. Audit And Finalize

```bash
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync

python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt
```

Main integrates only after reports exist, ownership passes, and validation
evidence is clear.

## Self-check

```bash
python3 /path/to/multi-agent-coding/adapters/codex/scripts/codex_self_check.py
python3 /path/to/multi-agent-coding/scripts/validate_all_adapters.py
```
