# Codex Multi-Agent Quickstart

Dependency-free Python 3. Reuses OpenClaw mission-control scripts.

## 0. Install Native Skill And Agents

From the extracted Codex package root:

```bash
python3 scripts/install_native_skills.py --client codex --scope primary --force
python3 scripts/install_native_skills.py --client codex --check
```

Reload Codex. Then ask Codex App or CLI:

```text
Use codex-multi-agent. Split this task into scoped task cards, spawn scoped Workers, use ssrd for read-only review if available, wait for results, then audit the diff before final delivery.
```

## 1. Generate Task Cards

```bash
cd /path/to/target-repo
python3 /path/to/codex-multi-agent/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/codex-multi-agent/adapters/codex/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

## 2. Sync Gates

```bash
python3 /path/to/codex-multi-agent/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync
```

## 3a. Full Mode: Native Codex Subagents

Prepare one spawn prompt per task card:

```bash
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex-native \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Main reads the returned `prompt_path`, then spawns a native Codex subagent with the returned `agent_type` and prompt contents.

Role mapping:

| Task role | Native agent |
| --- | --- |
| Explorer | `explorer` |
| Reviewer | `multi-agent-reviewer` or `explorer` |
| Verifier | `explorer` |
| Worker | `multi-agent-worker` or `worker` |

If the task card lists `may_use_skills: [ssrd]`, Main attaches or names `ssrd` for that subagent. If `ssrd` is unavailable, the subagent must report blocked.

## 3b. CLI Bridge

Ensure Codex CLI is authenticated in the user environment.

```bash
export CODEX_SANDBOX=workspace-write
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Overrides: `CODEX_MODEL`, `CODEX_BIN`, `CODEX_SANDBOX`, or launcher flags.

## 3c. Manual Fallback

Use only when native subagents and CLI bridge are unavailable:

```bash
python3 /path/to/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Open the returned `prompt_path` in a new Codex App session or task. The Worker must write both result reports before claiming completion.

## 4. Audit And Finalize

```bash
python3 /path/to/codex-multi-agent/adapters/openclaw/scripts/update_task_status.py \
  --state-dir .codex-multi-agent --sync

git diff --name-only > .codex-multi-agent/changed-files.txt
python3 /path/to/codex-multi-agent/adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

Main integrates only after reports exist, ownership passes, and validation evidence is clear.

## Self-check

```bash
python3 /path/to/codex-multi-agent/scripts/install_native_skills.py --client codex --check
python3 /path/to/codex-multi-agent/adapters/codex/scripts/codex_self_check.py
```
