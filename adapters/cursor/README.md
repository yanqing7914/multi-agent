# Cursor Multi-Agent Adapter

Thin Cursor layer over [`adapters/openclaw/`](../openclaw/) mission-control scripts. It does not duplicate task-card generation, gate sync, or audit logic.

**Fast path:** [QUICKSTART.md](QUICKSTART.md)

## What This Enables

Cursor App and Cursor CLI both get a native Agent Skill for the same workflow:

1. Cursor Main receives a multi-agent request.
2. Main generates scoped task cards under `.codex-multi-agent/`.
3. **Main dispatches each Worker/Reviewer by spawning a Cursor subagent directly** (in-App delegation) with the task-card prompt + scope. No external CLI required.
4. Each agent writes JSON + Markdown result reports.
5. Main runs gate sync, scope audit, and final delivery.

In Cursor App the **primary** path is in-App subagent delegation (step 3 above): the Main agent spawns a Cursor subagent per Worker/Reviewer. The local `agent` CLI bridge (`run_multi_agent.py --runtime cursor`) is an **optional scripted/CI path** (needs `agent` + tmux). Cursor 3's `/multitask` is a user-driven alternative; manual prompt handoff is the last-resort fallback.

## Install

From the extracted `cursor-multi-agent-pack-v0.3.1.zip` root:

```bash
python3 scripts/install_native_skills.py --client cursor --scope primary --force
python3 scripts/install_native_skills.py --client cursor --check
```

The installer writes native skill files to:

```text
~/.agents/skills/cursor-multi-agent
~/.cursor/skills/cursor-multi-agent
```

For workspace-level rules, keep or copy the bundled `.cursor/rules/multi-agent-coding.mdc`.

## Usage: Cursor App Full Mode (In-App Subagent Delegation — primary)

After the skill is installed and Cursor is reloaded, ask Cursor Agent:

```text
Use cursor-multi-agent. Split this change into scoped task cards, then for each task card spawn a Cursor subagent (Worker limited to allowed_paths; Reviewer read-only) to do the work and write JSON + Markdown result reports. Collect the reports, run scope audit, and deliver only after gates pass.
```

The Main agent dispatches each Worker/Reviewer by **spawning a Cursor subagent directly** — no external CLI needed. Worker write-scope is enforced by the task-card `allowed_paths` plus the post-hoc scope audit (`audit_worker_output.py`), and can be hardened with one git worktree per Worker (`tools/worktree_tool.py`). Main still collects reports and runs the audit before delivery.

If your Cursor agent cannot delegate to subagents, use `/multitask` (user-driven), the optional `agent` CLI bridge (below), or manual handoff.

## Alternative: `agent` CLI bridge (scripted / CI)

Optional. The bridge runs Cursor's terminal agent for shell/CI-driven Workers. The current binary is `agent` (legacy alias `cursor-agent` also accepted). Install it only if you need this path:

```bash
# macOS / Linux / WSL
curl https://cursor.com/install -fsS | bash

# Windows (native PowerShell)
irm 'https://cursor.com/install?win32=true' | iex
```

Reopen your shell and run `agent --version`. If not found, add `~/.local/bin` to `PATH`. The bridge also relies on `bash` + `tmux`, so on native Windows run it from WSL. Then, per task card:

```bash
python3 /path/to/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Run `python3 scripts/doctor.py --client cursor` for a guided readiness check.

## Manual Fallback

Use only if `agent` CLI is unavailable or the user explicitly wants manual handoff:

```bash
python3 /path/to/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

This writes `.codex-multi-agent/cursor-desktop/*.cursor.md`. Open or paste the prompt into Cursor Agent in the target workspace.

## Contract

| Artifact | Location |
| --- | --- |
| Task cards | `.codex-multi-agent/tasks/*.md` |
| Result Markdown | `.codex-multi-agent/results/*.md` |
| Result JSON | `.codex-multi-agent/results/*.json` |
| Manual prompts | `.codex-multi-agent/cursor-desktop/*.cursor.md` |
| Preflight | `adapters/openclaw/scripts/verify_workspace.py` |
| Schema | `adapters/openclaw/templates/result-report.md` |

## What Works Today

- Native Cursor Agent Skill install for App and CLI
- **In-App subagent delegation** as the primary Worker-dispatch path (no external CLI)
- Cursor rules pack via `.cursor/rules/multi-agent-coding.mdc`
- Optional `agent` CLI bridge (foreground + tmux-detached) for scripted/CI
- `/multitask` (user-driven) and prompt handoff as alternatives
- Shared gate/audit path via OpenClaw scripts

## Readiness

- `native_skill_ready=true`: Cursor can load the skill — and Main can dispatch Workers via in-App subagent delegation. This is the App path; **the `agent` CLI is not required for it**.
- `complete_worker_bridge_ready=true`: reported once the skill is installed (in-App delegation is the path). The `agent` CLI is optional and only powers the scripted/CI bridge.
- `bridge_bins` shows whether `agent`/`cursor-agent` are on PATH (only relevant for the optional scripted bridge).

## Self-check

```bash
python3 scripts/install_native_skills.py --client cursor --check
python3 scripts/doctor.py --client cursor        # friendly readiness report
python3 adapters/cursor/scripts/cursor_self_check.py
```
