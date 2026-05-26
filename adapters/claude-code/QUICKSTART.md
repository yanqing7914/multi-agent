# Claude Code Multi-Agent — Quickstart

Dependency-free Python 3. Reuses OpenClaw mission-control scripts.

## 1. Generate task cards

```bash
cd /path/to/target-repo
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/multi-agent-coding/adapters/claude-code/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

## 2. Validate bridge

```bash
python3 /path/to/multi-agent-coding/adapters/claude-code/scripts/claude_code_self_check.py
python3 /path/to/multi-agent-coding/scripts/validate_all_adapters.py
```

## 3a. OpenClaw ACP handoff

```bash
python3 /path/to/multi-agent-coding/adapters/claude-code/scripts/launch_claude_worker.sh \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --mode acp
```

Use printed `sessions_spawn` / `sessions_send` / `sessions_yield` in OpenClaw Main.

## 3b. Local one-shot

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime claude-code \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

**Quota warning:** Local `claude --print` is subject to account budget / 429 errors. The launcher exits non-zero with `"error": "quota_exhausted"` when detected. For production, use **3a ACP** instead.

## 4. Gates & audit

Follow [OpenClaw QUICKSTART](../openclaw/QUICKSTART.md) steps 5–7.
