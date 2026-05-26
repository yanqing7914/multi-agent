# OpenClaw Multi-Agent — Quickstart (fresh checkout)

Dependency-free Python 3. No `pip install`. No MCP.

## 1. Install the skill

From your clone of `multi-agent-coding`:

```bash
ln -s "$(pwd)/adapters/openclaw" ~/.openclaw/skills/openclaw-multi-agent
```

Or copy the folder to your OpenClaw skills directory. You only need `adapters/openclaw/` — not the whole monorepo in the skill path.

In OpenClaw/Her:

```text
Use $openclaw-multi-agent to coordinate Explorer, Worker, Reviewer, and Verifier sessions for this task.
```

## 2. Generate mission-control state

Run from the **target repo root** (the codebase you are changing):

```bash
cd /path/to/your/target-repo
python3 /path/to/multi-agent-coding/adapters/openclaw/scripts/create_task_cards.py \
  --from-yaml /path/to/multi-agent-coding/adapters/openclaw/examples/favorite-feature.yaml \
  --workspace-root "$(pwd)" \
  --out .codex-multi-agent
```

**Expected output** (truncated):

```json
{
  "ok": true,
  "workspace_root": "/path/to/your/target-repo",
  "tasks": 9,
  "out": ".codex-multi-agent/tasks",
  "ownership": ".codex-multi-agent/ownership.json",
  "status": ".codex-multi-agent/status.json"
}
```

Each task card under `.codex-multi-agent/tasks/` now includes:

- `workspace_root` / `target_repo` — absolute path; child session must `cd` here first
- `preflight_command` — shell lines to verify paths before work
- `required_paths` — must be readable before `status=completed`

## 3. Validate scripts (no agents)

```bash
cd /path/to/multi-agent-coding/adapters/openclaw
python3 scripts/validate_all.py
```

Or individually:

```bash
python3 scripts/create_task_cards.py --self-check
python3 scripts/update_task_status.py --self-check
python3 scripts/audit_worker_output.py --self-check
python3 scripts/verify_workspace.py --self-check
python3 scripts/run_local_demo.py --self-check
```

**Expected:** `validate_all.py` prints six `[PASS]` lines (including `adapter_artifacts`) and exits `0`; each script prints `{"ok": true, ...}`.

## 4. Local demo (deterministic gates)

From repo root:

```bash
python3 adapters/openclaw/scripts/run_local_demo.py --keep
# Optional: pin output — python3 .../run_local_demo.py --out /tmp/openclaw-demo --keep
```

**Expected:** JSON with `"ok": true`. By default the demo uses a system temp directory (removed unless `--keep`). Summary lists **Workspace / Preflight Issues** for the simulated false-completion reviewer.

**Audit contract:** `audit_worker_output.py` exit `0` only when `"ok": true` and `gate.status=passed`. Warnings ⇒ `ok=false`, gate `pending`, exit `2`. After Workers, recapture `changed-files.txt` and rerun `--write-audit` whenever the diff changes — otherwise `--sync` marks `scope_audit` stale.

## 5. OpenClaw session workflow (Golden Path)

1. **Sync gates** before each spawn wave:

   ```bash
   python3 adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync
   ```

2. **Spawn** using `openclaw_handoff` from the task card (`sessions_spawn` / `sessions_send` / `sessions_yield`).

3. **Child session first actions** (critical — dogfood failure mode):
   - `cd` to the absolute `workspace_root` from the card
   - Run every line under `preflight_command`
   - If paths are missing: `status=blocked`, `required_paths_verified=false` — never fake review

4. **Result reports** — write both JSON and Markdown paths from `result_report_paths`:
   - Set `workspace_observed` to `pwd` after `cd`
   - List real paths in `files_read`
   - Set `required_paths_verified=true` only when paths were actually read

5. **After each wave:**

   ```bash
   python3 adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync
   ```

6. **After Workers** — capture diff and audit:

   ```bash
   git diff --name-only > .codex-multi-agent/changed-files.txt
   python3 adapters/openclaw/scripts/audit_worker_output.py \
     --ownership .codex-multi-agent/ownership.json \
     --results .codex-multi-agent/results \
     --changed-files .codex-multi-agent/changed-files.txt \
     --write-audit --state-dir .codex-multi-agent
   ```

7. **Final summary:**

   ```bash
   python3 adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --summarize
   ```

## Workspace workaround

OpenClaw may **not** honor `sessions_spawn` cwd. Task cards therefore use an **absolute** `workspace_root`. Every subagent must:

```bash
cd "<workspace_root from task card>"
pwd
```

before reading or editing. If a reviewer completes from `/tmp` or another clone, sync will downgrade them to `blocked` and gates will fail.

## See also

- [README.md](README.md) — full adapter docs and Golden Path detail
- [examples/dogfood-openclaw.yaml](examples/dogfood-openclaw.yaml) — adapter-only dogfood task
- [../../docs/roadmap.md](../../docs/roadmap.md) — v1 done criteria vs v2 MCP
