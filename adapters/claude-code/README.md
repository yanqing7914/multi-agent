# Claude Code Multi-Agent Adapter

Thin Claude Code layer over [`adapters/openclaw/`](../openclaw/) mission-control scripts.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## Install

No pip install. Python 3 only.

For **ACP path**: use with `adapters/openclaw/` inside OpenClaw/Her.

For **local path**: install Claude Code CLI (`claude`) and authenticate locally.

## Usage

### Path A — OpenClaw ACP (preferred in OpenClaw)

```bash
python3 adapters/claude-code/scripts/launch_claude_worker.sh \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md \
  --mode acp
```

Prints spawn/send/yield handoff JSON. Main pastes the task card into `sessions_send`.

### Path B — Local one-shot

```bash
python3 /path/to/multi-agent-coding/scripts/run_multi_agent.py \
  --runtime claude-code \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Runs:

```text
claude --print --permission-mode bypassPermissions "<preflight + task card prompt>"
```

### Expected output (local success)

```json
{
  "ok": true,
  "runtime": "claude-code",
  "mode": "local",
  "result_markdown": ".../.codex-multi-agent/results/T002-worker-backend.md",
  "result_json_exists": true
}
```

On failure (non-zero CLI exit, 429/budget/quota/`Request rejected` in log, missing artifacts), the launcher prints `"ok": false`, `"error": "quota_exhausted"` (or similar), and exits non-zero.

## Self-check

```bash
python3 adapters/claude-code/scripts/claude_code_self_check.py
```

## What works today

- Preflight before local `claude --print`
- ACP handoff JSON for OpenClaw Main (no spawn from script)
- Shared gate/audit via OpenClaw scripts
- Result tee + JSON extraction helper

## Limitations

- ACP mode does not spawn sessions — OpenClaw Main must run handoff.
- **Local CLI quota risk:** `claude --print` can return HTTP 429 / budget errors; the launcher detects these and reports `quota_exhausted`. For production multi-agent runs inside OpenClaw, **prefer the ACP path** (`--mode acp`) so sessions are managed by OpenClaw, not one-shot local quota.
- **Guarded dogfood:** `dogfood_claude.py` runs local mode but reports `"status": "skipped"` (exit 0) when quota/budget patterns appear — it does **not** fail the overall validation run.
- `bypassPermissions` is powerful; use only on trusted scoped tasks.
- Claude Code session features beyond `--print` are not wrapped yet.

### Guarded dogfood (best-effort)

```bash
python3 adapters/claude-code/scripts/dogfood_claude.py \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md

# Self-check: 429 fixture must report skipped (not ok)
python3 adapters/claude-code/scripts/dogfood_claude.py --self-check
```

When budget is exceeded, output includes `"status": "skipped"`, `"reason": "budget exceeded"`. Use **ACP** for production OpenClaw workflows.
