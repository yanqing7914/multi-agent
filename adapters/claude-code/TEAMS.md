# Claude Code Agent Teams (Experimental)

Map Claude Code's experimental **Agent Teams** onto this framework's contract:
task cards + ownership boundaries (`allowed_paths` / `role` / `write_permission`)
+ result reports + audit gates (`scope_audit`).

Agent Teams is one complete App/CLI orchestration path for Claude Code, alongside
the bundled delegated subagents, the `claude --print` CLI bridge, and OpenClaw ACP
(see [SKILL.md](SKILL.md) execution modes). Main still owns the final diff and the
scope audit no matter which path you pick.

## When To Use Agent Teams vs Delegated Subagents

First apply `checklists/should-use-multi-agent.md`. If multi-agent is justified,
choose the shape:

Use **Agent Teams** when:

- Teammates must discuss or challenge each other (design debate, cross-review, "two
  Workers reconcile a shared interface").
- Work splits cleanly across layers and runs in parallel — e.g. one teammate per
  `backend/**`, `frontend/**`, and `tests/**`.
- A longer session benefits from a shared task board with dependencies and
  auto-unblock instead of one-shot delegations.

Use **delegated subagents** (the bundled `multi-agent-worker/reviewer/verifier`)
when:

- The task is focused and only needs a result handed back, with no back-and-forth.
- You want lower token cost and a simpler control flow.

Stay on the Quick Path (no team) when the checklist says so: single-file or obvious
change, root cause already known, or **no safe ownership split**. If multiple
teammates would edit the same files, split `allowed_paths` or isolate with worktrees
first (see Conflict And Security) — otherwise they will overwrite each other.

## Enable And Prerequisites

1. Turn on the experimental flag in settings.json (`~/.claude/settings.json` or a
   project `.claude/settings.json`):

```json
{
  "env": { "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1" }
}
```

   (Or export `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` as an environment variable.)
   Requires Claude Code v2.1.178+, where spawning a teammate auto-creates the team
   and cleanup happens automatically on exit — no manual team bookkeeping.

2. Pick a teammate mode. `teammateMode: auto` (default) uses `tmux` split-panes when
   available and falls back to `in-process` otherwise. Split-pane observe/interrupt
   needs tmux or iTerm2; Windows Terminal and the VS Code integrated terminal do not
   support split-pane — use `in-process` there.

3. Install this skill's bundled role definitions so they can be reused as teammates:

```bash
python3 scripts/install_native_skills.py --client claude --scope primary --force
python3 scripts/install_native_skills.py --client claude --check
```

   This writes `~/.claude/agents/multi-agent-worker.md`, `multi-agent-reviewer.md`,
   and `multi-agent-verifier.md`, plus the `claude-code-multi-agent` skill under
   `~/.claude/skills/` (user scope).

   Note: a subagent definition's `skills:` / `mcpServers:` frontmatter is **not**
   applied when that definition runs as a teammate (teammates load skills and MCP
   from project/user settings). Because the installer puts `claude-code-multi-agent`
   in user scope, teammates still pick it up. The definition's `tools` allowlist and
   `model` **are** honored, and the definition body is appended to the teammate's
   system prompt.

## Contract Mapping

| Claude Agent Teams | This framework | Notes |
| --- | --- | --- |
| Lead session | Main | Lead is fixed; owns final diff + scope audit + delivery. |
| Teammate | Worker / Reviewer / Verifier | Spawn each teammate from a bundled definition (`multi-agent-worker` / `-reviewer` / `-verifier`), or any project/user/plugin/CLI subagent definition. |
| Shared task board `~/.claude/tasks/{team}/` (pending / in_progress / completed) | Task cards `.codex-multi-agent/tasks/*.md` + `status.json` gates | `ownership.allowed_paths` is still the write boundary; Reviewer/Verifier remain read-only. The board tracks progress; ownership.json + the audit enforce scope. |
| Task dependencies + auto-unblock | Task card `dependencies` + gate phases | Phases run `explorers_complete` -> `workers_complete` -> `review_complete` -> `verify_complete` -> `scope_audit` -> `final_delivery`. A teammate's task unblocks when its `dependencies` complete, mirroring the gate it sits behind. |
| Plan approval (read-only plan -> lead approves -> implement) | Worker emits a read-only plan first; Main approves, then authorizes the write | Keep `write_permission: false` until the plan is approved; optionally drop the approval note under `.codex-multi-agent/approvals/`. |

Boundary alignment that comes for free: the bundled Reviewer and Verifier definitions
declare only `tools: Read, Grep, Glob, Bash` (no `Edit` / `Write`), so as teammates
they stay read-only at the tool-allowlist layer. The Worker definition adds
`Edit, Write` but must stay inside its `allowed_paths` (logical boundary) and ideally
its own worktree (physical boundary).

## Wire The Scope Audit As A Completion Gate

Turn `scope_audit` into a hard gate for teammates with a `TaskCompleted` hook: the
hook runs the audit, and a non-zero exit (exit code 2) blocks the "completed"
transition and feeds the violation text back to the teammate.

This wiring is exact, not aspirational: `adapters/openclaw/scripts/audit_worker_output.py`
already returns **exit code 2** whenever the `scope_audit` gate is not `passed`
(out-of-scope writes, secret/blocked paths, or two Workers touching the same file),
and exit code 0 when it passes — precisely the signal a `TaskCompleted` hook consumes.

Approach (Agent Teams and its hooks are experimental — confirm the exact hooks
schema against your installed Claude Code version; assume no more than the documented
`type: command` + `command` fields and the exit-code-2 block):

```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 adapters/openclaw/scripts/capture_changed_files.py --state-dir .codex-multi-agent && python3 adapters/openclaw/scripts/audit_worker_output.py --ownership .codex-multi-agent/ownership.json --results .codex-multi-agent/results --changed-files .codex-multi-agent/changed-files.txt --write-audit --state-dir .codex-multi-agent"
          }
        ]
      }
    ]
  }
}
```

- Run the hook from the repo root (or use absolute paths). It captures the changed
  files, reads each teammate's result report from `.codex-multi-agent/results/`, and
  writes `audits/latest.json`.
- A failing or still-pending audit exits non-zero, so the teammate cannot mark the
  task complete until its writes are in scope and a report exists — the violation
  detail returned by exit 2 tells it what to fix.
- When each teammate runs in its own git worktree, capture that worktree's diff (run
  the `git diff` from the worktree root) rather than the main tree.
- The other team hooks can mirror existing steps without replacing the scope gate:
  `TaskCreated` can sanity-check that a claimed task has a matching ownership entry,
  and `TeammateIdle` can run `update_task_status.py --state-dir .codex-multi-agent --sync`.
  Only the `TaskCompleted` scope-audit block is mandatory.

## Conflict And Security

- Teammates editing the same file overwrite each other. Divide the filesystem with
  `ownership.allowed_paths` (one file domain per teammate); the audit flags any file
  that more than one Worker reports or that falls outside a Worker's scope.
- For physical isolation, give each Worker its own git worktree + branch:

```bash
python3 tools/worktree_tool.py --action plan --ownership .codex-multi-agent/ownership.json --create
```

  This creates one `multi-agent/<task>-<session>` worktree+branch per Worker and
  skips read-only roles (`write_permission: false`). Point each teammate's working
  directory at its worktree, then merge or PR the branch.
- Keep Explorer / Reviewer / Verifier read-only: their tool allowlists omit `Edit` /
  `Write` and their `write_permission` is `false`.
- Never write secrets into result reports or the task board. The audit treats secret
  patterns (`.env`, `*.pem`, `*.key`, `**/credentials.json`, ...) as blocked paths
  and fails when a changed file matches them.

## Honest Limits

- Agent Teams is experimental and token-expensive: each teammate is a full Claude Code
  instance with its own context window, CLAUDE.md, MCP, and skills.
- One team per session; teams cannot nest; the lead is fixed; a teammate's permissions
  are inherited from the lead at spawn time (you can adjust them per teammate after).
- Split-pane observe/interrupt needs tmux or iTerm2; otherwise use `in-process`.
- When you do not need a team, prefer the bundled delegated subagents or the
  `claude --print` bridge:

```bash
python3 scripts/run_multi_agent.py --runtime claude-code --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

- Main remains responsible for the final `git diff` / scope audit and delivery,
  regardless of which orchestration path was used.

## See Also

- [SKILL.md](SKILL.md) · [README.md](README.md) · [QUICKSTART.md](QUICKSTART.md)
- `checklists/should-use-multi-agent.md`
- `adapters/openclaw/scripts/audit_worker_output.py` · `adapters/openclaw/scripts/update_task_status.py` · `adapters/openclaw/scripts/create_task_cards.py`
- `tools/worktree_tool.py`
