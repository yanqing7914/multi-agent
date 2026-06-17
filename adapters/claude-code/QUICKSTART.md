# Claude Multi-Agent Quickstart

Dependency-free Python 3. Reuses OpenClaw mission-control scripts.

## 0. Choose Claude Surface

| Surface | Use |
| --- | --- |
| Claude Desktop / Claude.ai | `--runtime claude-desktop` to generate custom-skill prompts |
| Claude Code CLI | `--runtime claude-code` for local one-shot workers |
| OpenClaw / Her | `--runtime claude-code --mode acp` for session orchestration |

## 1. Generate Task Cards

```bash
cd /path/to/target-repo
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/multi-agent-coding/adapters/claude-code/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

## 2a. Claude Desktop / Claude.ai Prompt

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime claude-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Use the returned `prompt_path` inside Claude Desktop / Claude.ai custom skill
context or paste it into a Claude project/chat that has repository tooling.

## 2b. OpenClaw ACP Handoff

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime claude-code \
  --mode acp \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Use printed `sessions_spawn` / `sessions_send` / `sessions_yield` in OpenClaw Main.

## 2c. Local Claude Code One-shot

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime claude-code \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Quota warning: local `claude --print` is subject to account budget / 429 errors.
The launcher exits non-zero with `"error": "quota_exhausted"` when detected.

## 3. Gates And Audit

Follow [OpenClaw QUICKSTART](../openclaw/QUICKSTART.md) gate sync and audit steps.

## Self-check

```bash
python3 /path/to/multi-agent-coding/adapters/claude-code/scripts/claude_code_self_check.py
python3 /path/to/multi-agent-coding/scripts/validate_all_adapters.py
```
