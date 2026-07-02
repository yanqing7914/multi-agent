---
name: cursor-multi-agent
description: Cursor-specific thin adapter for multi-agent coding. Use when Cursor App or Cursor CLI should coordinate scoped Explorer/Worker/Reviewer/Verifier roles with task cards, result reports, and scope audit. In Cursor App the Main agent dispatches each Worker/Reviewer by spawning a Cursor subagent (delegation) directly; the local `agent` CLI bridge is only for scripted/CI runs. Do not use for simple single-agent edits.
---

# cursor-multi-agent

Thin Cursor adapter over the shared OpenClaw mission-control core. Reuse
`adapters/openclaw/scripts/*` for task cards, gates, audits, and demos.

## When To Use

Use when:

- coordinating from Cursor App or Cursor CLI as Main Agent
- the user asks for multiple agents, Workers, Reviewers, Verifiers, or parallel review
- the task needs scoped `allowed_paths`, `blocked_commands`, result reports, and final diff audit

Do not use when:

- the task is a quick single-agent edit
- the user wants OpenClaw `sessions_spawn`; use `adapters/openclaw/`

## How To Dispatch A Worker In Cursor App (primary path)

In Cursor App the Main agent (you) dispatches a Worker by **spawning a Cursor
subagent yourself** — you do NOT need the external `agent` CLI for this. For each
Worker/Reviewer task card:

1. Generate task cards under `.codex-multi-agent/` (see Golden Path).
2. For each task card, **spawn a subagent** (Cursor's delegation / Agents
   capability) and give it: the task-card body, its `role`, `allowed_paths`,
   `blocked_paths`, authorized `may_use_skills`, and the two `result_report_paths`.
   Instruct a Worker to edit only within `allowed_paths`; instruct a
   Reviewer/Explorer/Verifier to stay read-only (`files_changed` empty).
3. Wait for each subagent to write its JSON + Markdown result report.
4. As Main: capture changed files (staged + unstaged + untracked) with
   `python3 adapters/openclaw/scripts/capture_changed_files.py --state-dir .codex-multi-agent`,
   run the scope audit, sync gates, then deliver.

This is the same controlled loop other clients run; in Cursor the role
write-permission is enforced by the task-card instructions plus the post-hoc
scope audit (`audit_worker_output.py`), and can be hardened with one git
worktree per Worker (`tools/worktree_tool.py`). If your Cursor agent cannot
delegate to subagents, fall back to `/multitask` (user-driven), the `agent` CLI
bridge, or manual handoff — see Execution Modes.

## Execution Modes

| Mode | Use when | How |
| --- | --- | --- |
| **In-App subagent delegation (primary)** | **Cursor App, Main can delegate to subagents** | **Main spawns one Cursor subagent per Worker/Reviewer with the task-card prompt + scope; collects reports; audits. No external CLI needed.** |
| App `/multitask` | Cursor 3 App, user-driven | User types `/multitask` (parallel subagents, each own worktree/PR) or `/sdk`; see `SDK.md` |
| Cursor SDK / headless | Programmatic or CI runs | `@cursor/sdk` or headless `agent -p --output-format json`; generate run specs with `scripts/prepare_cursor_sdk.py`; see `SDK.md` |
| Cursor CLI bridge | Scripted Workers from a shell | Run `scripts/run_multi_agent.py --runtime cursor` (needs `agent` CLI + tmux; deterministic CI path) |
| Manual handoff fallback | No delegation, no `agent` CLI | Run `--runtime cursor-desktop` and paste/open prompts in Cursor Agent |

In Cursor App the **primary** way to dispatch Workers is for the Main agent to
**spawn subagents directly** (see "How To Dispatch A Worker In Cursor App").
This does not require the `agent` CLI. The `agent` CLI bridge
(`run_multi_agent.py --runtime cursor`) is for scripted/CI use and needs both the
`agent` binary and `tmux` on PATH (on native Windows, run it from WSL).

## Golden Path

1. Install the package with `scripts/install_native_skills.py --client cursor --scope primary --force`.
2. Restart/reload Cursor so it discovers `cursor-multi-agent`.
3. Generate `.codex-multi-agent/` task cards from the target repo.
4. **Dispatch each Worker/Reviewer by spawning a Cursor subagent yourself** (primary path; see "How To Dispatch A Worker In Cursor App"). No external CLI required.
5. Main captures `git diff`, runs scope audit + gate sync, then delivers.

Alternative (scripted/CI) — the `agent` CLI bridge instead of step 4:

```bash
# Needs `agent` CLI + tmux on PATH (on native Windows run from WSL):
python3 /path/to/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Install the CLI with `irm 'https://cursor.com/install?win32=true' | iex` (Windows)
or `curl https://cursor.com/install -fsS | bash`. Check readiness with
`scripts/doctor.py --client cursor`. If neither delegation nor the CLI is
available, use `--runtime cursor-desktop` for manual prompt handoff.

## Skill Routing

- Reviewer cards may authorize review skills such as `ssrd` with `may_use_skills: [ssrd]`.
- Worker cards may authorize implementation skills only when the user or Main explicitly allows them.
- Authorized skill names must be included in the Worker/Reviewer prompt.
- If an authorized skill is unavailable, the agent must report `status=blocked`.
- Workers may not use skills to expand paths, shell commands, network access, credentials, git writes, or role permissions.

## Validation

```bash
python3 scripts/install_native_skills.py --client cursor --check
python3 scripts/doctor.py --client cursor
python3 adapters/cursor/scripts/cursor_self_check.py
python3 scripts/validate_all_adapters.py
```
