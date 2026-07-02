# Cursor Native Orchestration Paths (SDK + Headless CLI)

This adapter has always shipped one deterministic automation path: the local
`agent` CLI **bridge** (`scripts/launch_cursor_worker.py`, tmux + `agent -p`).
This document adds the **native Cursor orchestration paths** so Cursor App and
Cursor CLI can drive the same multi-agent contract end to end.

There are three native paths, plus the existing bridge:

| Path | Surface | Parallelism | Best for |
| --- | --- | --- | --- |
| **A. App Agents Window** | Cursor App `/multitask`, `/worktree`, `/sdk`, `.cursor/agents/` | Native (worktree + PR per subagent) | Interactive, human-in-the-loop fan-out |
| **B. Headless CLI** | `agent -p --output-format json\|stream-json` | You orchestrate (one process per Worker) | Ad-hoc / scripted runs, your own runner |
| **C. Programmatic SDK** | `@cursor/sdk` (`Agent` → `Run`), local / cloud / self-hosted | You orchestrate (`Promise.all`, worktrees) | Apps, bots, CI-like automation |
| Bridge (existing) | `launch_cursor_worker.py` (tmux + `agent -p`) | Main launches per task card | Deterministic scripted/audited Worker runs |

> **Bridge vs native:** the bridge is the *deterministic script path* — it wraps
> `agent -p` with preflight, result extraction, timeout markers, and foreground
> waiting so Main can audit outcomes. Paths A–C are *native Cursor parallel
> paths* you reach for when you want the App's Agents Window or the SDK's
> programmatic control. All four enforce the **same** task-card + result-report
> contract below.

---

## Shared contract (every path obeys this)

All paths consume the mission-control state produced by
`adapters/openclaw/scripts/create_task_cards.py`:

- **Task cards** — `.codex-multi-agent/tasks/<task_id>-<session>.md`
- **Ownership** — `.codex-multi-agent/ownership.json` (per task: `role`,
  `write_permission`, `allowed_paths`, `result_report_json/markdown`)
- **Worker scope** — a Worker edits ONLY its `allowed_paths`, never secrets /
  blocked paths, no dependency installs / deploys / pushes, no scope expansion.
- **Result reports** — every Worker writes BOTH a JSON and a Markdown report
  (schema: `adapters/openclaw/templates/result-report.md`) before completion.
- **Main owns the gates** — after Workers finish, Main runs gate sync + scope
  audit and only then delivers. None of these paths self-deliver.

`prepare_cursor_sdk.py` turns `ownership.json` into a ready-to-run spec for the
SDK/CLI paths and bakes the full contract into each Worker prompt.

---

## 0. Generate the run-spec (shared by paths B and C)

From the target repo root, after task cards exist:

```bash
python adapters/cursor/scripts/prepare_cursor_sdk.py \
  --ownership .codex-multi-agent/ownership.json
```

This is **dry** — it never calls `agent` or `npm`. It writes:

- `.codex-multi-agent/cursor-sdk/run-spec.json` — one entry per write-permission
  Worker: `{task_id, session_name, workspace_root, allowed_paths,
  result_report_paths, prompt, prompt_path, headless_command}`.
- `.codex-multi-agent/cursor-sdk/prompts/<task_id>-<session>.md` — the scoped
  Worker prompt (reuses `adapters/_shared/bridge.py:build_worker_prompt` when the
  task card is present, otherwise an ownership-only fallback with the same
  contract).

Useful flags:

- `--out <path>` — change where `run-spec.json` is written (prompts land in a
  sibling `prompts/` dir).
- `--print-commands` — emit copy-paste / bash-pipeable headless commands instead
  of the JSON summary (see Path B).

Only `role: Worker` tasks with `write_permission: true` get a spec; Explorers,
Reviewers, and Verifiers are intentionally excluded (they are read-only).

---

## Path A — Cursor App: Agents Window / `/multitask` / `/sdk`

Cursor App loads this skill (`cursor-multi-agent`) natively. The App's **Agents
Window** can fan a single request into parallel subagents, each in its own git
worktree, each able to open a PR.

How it maps onto the contract:

1. Main (the App agent running this skill) generates task cards as usual.
2. Use `/multitask` to spin up one subagent per Worker, or define subagents under
   `.cursor/agents/`. Use `/worktree` so parallel Workers cannot overwrite each
   other (this mirrors `tools/worktree_tool.py`, which plans one worktree per
   Worker from `ownership.json`).
3. Seed each subagent with its scoped prompt: open
   `.codex-multi-agent/cursor-sdk/prompts/<task_id>-<session>.md` (or paste the
   task card). The prompt already states `allowed_paths` and the dual
   result-report requirement.
4. `/sdk` is the in-App skill that guides programmatic SDK usage — switch to
   Path C when you want code instead of chat.
5. Main collects result reports, then runs gate sync + scope audit.

**Status:** wiring the App's `/multitask` directly to this adapter's `run-spec`
is a manual paste today (open the generated prompt in each subagent). For a fully
scripted hand-off, use the CLI bridge or Path B/C below.

---

## Path B — Headless CLI: `agent -p --output-format json|stream-json`

The Cursor CLI (`agent`, legacy alias `cursor-agent`) runs headless. Generate the
commands straight from the run-spec:

```bash
python adapters/cursor/scripts/prepare_cursor_sdk.py \
  --ownership .codex-multi-agent/ownership.json \
  --print-commands
```

Each line is runnable as-is (it `cd`s into the Worker's `workspace_root` first):

```bash
cd '/abs/repo' && agent -p '@/abs/.codex-multi-agent/cursor-sdk/prompts/T002-worker-backend.md' --force --output-format json
```

Output formats:

- `--output-format json` — a single JSON result object (easiest to parse for a
  one-shot Worker).
- `--output-format stream-json` — an NDJSON event stream (system / user /
  assistant / tool_call / thinking / status / request / task). Add
  `--stream-partial-output` for token-level deltas.
- `--output-format text` — plain text (what the tmux bridge uses).

`@<prompt-file>` tells `agent` to read the prompt from a file; if your CLI build
predates `@`-file prompts, substitute `agent -p "$(cat <prompt-file>)" ...`.

**Relationship to the bridge:** `launch_cursor_worker.py` wraps the *same*
`agent -p` invocation but adds tmux session management, `verify_workspace.py`
preflight, result-JSON extraction, Markdown companion generation, timeout
markers, and a `--foreground` synchronous mode. Reach for the bridge when you
want a deterministic, audited Worker run; reach for Path B when you want the raw
command for a quick run or to feed your own orchestrator.

After the runs, collect the result reports and audit:

```bash
python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync
python3 adapters/openclaw/scripts/capture_changed_files.py --state-dir .codex-multi-agent  # staged + unstaged + untracked
python adapters/openclaw/scripts/audit_worker_output.py \
  --ownership .codex-multi-agent/ownership.json \
  --results .codex-multi-agent/results \
  --changed-files .codex-multi-agent/changed-files.txt \
  --write-audit --state-dir .codex-multi-agent
```

---

## Path C — Programmatic `@cursor/sdk` (local / cloud / self-hosted)

The `@cursor/sdk` (TypeScript, public beta) runs Cursor agents from code using
the `Agent` → `Run` model. A ready-to-extend reference launcher lives in
[`sdk/run_workers.mjs`](sdk/run_workers.mjs); it consumes the same
`run-spec.json`.

```bash
cd adapters/cursor/sdk
npm install                      # pulls @cursor/sdk (Node path; not run in CI)
export CURSOR_API_KEY=cursor_... # or: cursor login
node run_workers.mjs /abs/.codex-multi-agent/cursor-sdk/run-spec.json
#   or: CURSOR_SDK_RUN_SPEC=/abs/.../run-spec.json npm start
```

For each Worker the launcher does `Agent.create(...)` → `agent.send(prompt)` →
streams `run.stream()` events → `run.wait()`, then reports whether the two
result-report files were written. It distinguishes a thrown `CursorAgentError`
(the run never started — auth/config/network, exit 1) from
`result.status === "error"` (the run executed and failed, exit 2).

Runtime selection (`CURSOR_SDK_RUNTIME`, default `local`):

- **local** — runs on your machine against the Worker's `workspace_root`, so it
  can write the local `.codex-multi-agent/results/*` files the contract expects.
  This is the right default for the file-based mission-control flow.
- **cloud** — runs on a Cursor-hosted VM against a freshly cloned repo and
  (`autoCreatePR`) opens a PR visible in the App's Agents Window. Set
  `CURSOR_SDK_CLOUD_REPO=<git url>` (and optionally `CURSOR_SDK_CLOUD_REF`). Note
  the local result-report files will NOT appear on your disk in cloud mode —
  collect outcomes from the PR / Agents Window, or have the Worker commit its
  reports into the repo.
- **self-hosted** — point the SDK at a private/self-hosted pool per the Cursor
  docs; the contract is unchanged.

> This Node path is intentionally outside the dependency-free Python core. It
> requires `npm install` and Cursor auth, drives real agents, and is **not** run
> by `scripts/validate_all_adapters.py`. The dependency-free gate is
> `prepare_cursor_sdk.py --self-check`.

True parallelism (the shape `/multitask` uses): give each Worker its own git
worktree and run the SDK calls concurrently.

```bash
python tools/worktree_tool.py --action plan --create \
  --ownership .codex-multi-agent/ownership.json
# point each worker.cwd at its worktree, then Promise.all(...) the runs
```

---

## Which path should I use?

- **In Cursor App, interactive** → Path A (Agents Window / `/multitask`), or the
  bridge for a deterministic scripted Worker.
- **Quick scripted/manual run, no Node** → Path B (`--print-commands`).
- **Building an app / bot / automation** → Path C (`@cursor/sdk`).
- **Deterministic, audited, CI-style scripted Workers** → the existing bridge
  (`run_multi_agent.py --runtime cursor`).

All four end the same way: collect result reports → gate sync → scope audit →
deliver only after gates pass.

---

## Self-check

```bash
python adapters/cursor/scripts/prepare_cursor_sdk.py --self-check
node --check adapters/cursor/sdk/run_workers.mjs   # optional: validates JS syntax only
```
