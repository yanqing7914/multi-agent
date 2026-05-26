# Roadmap: v1 → v2 → v3

This repository evolves in three layers. Each layer keeps **Main accountable**, uses **task cards as the portable contract**, and treats **handoffs as logic gates** rather than vague suggestions.

## v1 — Prompt + scripts (current)

**Goal:** Usable multi-agent coding without MCP or IDE plugins.

| Component | What it does |
| --- | --- |
| Root `SKILL.md` | Collaboration protocol for Codex/Cursor/Claude-style agents |
| `adapters/openclaw/` | OpenClaw/Her skill with session tool mapping |
| `.codex-multi-agent/` | Local mission-control state (gitignored by default) |

**v1 state layout:**

```text
.codex-multi-agent/
  status.json          # gate + task status (source of truth for Main)
  ownership.json       # path ownership + result report paths + workspace_root
  run-plan.json        # ordered Explorer → Worker → Reviewer → Verifier → audit → delivery
  tasks/               # portable task cards
  results/             # JSON + Markdown result reports
  findings/            # aggregated reviewer findings
  approvals/           # skill-use approvals (manual in v1)
  audits/              # scope audit JSON from audit_worker_output.py
  summary/             # run-summary.md from update_task_status.py --summarize
  changed-files.txt    # optional git diff capture
```

**v1 scripts (dependency-free Python):**

```bash
python adapters/openclaw/scripts/create_task_cards.py --from-yaml adapters/openclaw/examples/favorite-feature.yaml --out .codex-multi-agent --workspace-root "$(pwd)"
python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --sync
python adapters/openclaw/scripts/audit_worker_output.py --ownership .codex-multi-agent/ownership.json --results .codex-multi-agent/results --write-audit
python adapters/openclaw/scripts/update_task_status.py --state-dir .codex-multi-agent --summarize
python adapters/openclaw/scripts/run_local_demo.py --self-check
```

### v1 done criteria (product-quality bar)

All of the following must pass on a fresh checkout:

| # | Criterion | How to verify |
| --- | --- | --- |
| 1 | Install path documented | Follow `adapters/openclaw/QUICKSTART.md` symlink step |
| 2 | Task cards include absolute `workspace_root` / `target_repo` and `preflight_command` | Inspect `.codex-multi-agent/tasks/*.md` after `create_task_cards.py` |
| 3 | Subagent workspace guidance explicit | Cards say to `cd` before reads; README documents OpenClaw cwd workaround |
| 4 | Anti-false-completion gates | `required_paths_verified=false` → task `blocked`, gate fails |
| 5 | Thin-evidence blocking | Reviewer `completed` + `files_read=[]` + concrete `required_paths` → `blocked` |
| 6 | Scope audit | `audit_worker_output.py` flags out-of-scope, secrets, non-Worker edits, missing reports |
| 7 | Deterministic local demo | `run_local_demo.py --self-check` exits 0 without spawning agents |
| 8 | Script self-checks | `python3 adapters/openclaw/scripts/validate_all.py` (five checks incl. `run_local_demo`) |
| 9 | `openclaw_adapter` path map | Module name maps to `adapters/openclaw/**` in generated cards |
| 10 | Run summary for Main | `--summarize` includes gates, tasks, preflight issues, findings |

**Explicit gates in v1:**

1. `explorers_complete` — Explorer reports present; no false/thin completion
2. `workers_complete` — Worker reports present; preflight valid
3. `review_complete` — Reviewer reports present; preflight valid
4. `verify_complete` — Verifier validation recorded
5. `scope_audit` — `audit_worker_output.py` passes (`audits/latest.json` `ok: true`)
6. `final_delivery` — all upstream gates passed; Main summarizes and delivers

OpenClaw Main runs commands in each task card's `main_commands`. Scripts update files only; they do not spawn sessions.

## v2 — MCP state server

**Status: v1 in** ✅ — [`mcp/multi-agent-coordinator/`](../mcp/multi-agent-coordinator/)

**Goal:** Same contract as v1, exposed as tools so any MCP client can coordinate without copy-pasting commands.

See [`docs/mcp-format.md`](mcp-format.md) for the tool surface:

- `create_task`, `list_tasks`, `get_task`, `update_task_status`
- `record_result`, `record_finding`, `approve_skill_use`
- `audit_scope`, `generate_final_report`

v2 maps directly onto v1 directories:

| v1 file/dir | v2 MCP tool |
| --- | --- |
| `tasks/` | `create_task`, `get_task` |
| `status.json` | `update_task_status`, `list_tasks` |
| `results/` | `record_result` |
| `findings/` | `record_finding`, `summarize_review` |
| `approvals/` | `request_skill_use`, `approve_skill_use` |
| `audits/` | `audit_scope` |

The skill remains responsible for workflow decisions; MCP stores state and exposes coordination tools. **Do not** require MCP for OpenClaw v1 workflows.

Self-check: `python3 mcp/multi-agent-coordinator/scripts/self_check.py`

## v3 — IDE / task panel

**Status: v1 in** ✅ — [`ide/multi-agent-panel/`](../ide/multi-agent-panel/)

**Goal:** Visual mission control inside VS Code / Cursor (local web UI; no extension yet).

UI surfaces (read `.codex-multi-agent/` directly):

- **Task board** — pending / running / blocked / completed by role
- **Findings view** — reviewer severity, file/line navigation
- **Approval center** — skill-use requests (read from `approvals/`)
- **Scope audit panel** — latest audit JSON + optional `--write` rerun
- **Final report** — preview from `summary/run-summary.md`

Launch: `python3 ide/multi-agent-panel/server.py --state-dir .codex-multi-agent --port 9876`

Self-check: `python3 ide/multi-agent-panel/scripts/self_check.py`

## Version alignment

```text
v1  Prompt + scripts + .codex-multi-agent/     ← OpenClaw + Cursor/Codex/Claude bridges
v2  multi-agent-coordinator-mcp (v1 in)        ← mcp/multi-agent-coordinator/
v3  Mission-control task panel (v1 in)         ← ide/multi-agent-panel/
```

Client-specific adapters (OpenClaw, Cursor, Codex, Claude Code) stay thin: they translate native session/spawn APIs into task cards and result reports. The contract stays stable across clients.

## Cross-client adapters — v1 in (with caveats)

| Adapter | Status | Caveats |
| --- | --- | --- |
| `adapters/openclaw/` | **Production v1** ✅ | Reference implementation; full gate demo |
| `adapters/cursor/` | **Usable + real dogfood** ✅ | `agent` + tmux; tmux spawn is fire-and-forget — Main polls results; `--foreground` for sync debug |
| `adapters/codex/` | **Usable + real dogfood** ⚠ | `codex` CLI + auth; default `CODEX_SANDBOX=workspace-write`; requires result JSON on disk |
| `adapters/claude-code/` | **Contract validated** ⚠ | Local CLI hits quota/429; launchers detect budget errors; **prefer ACP** in OpenClaw |
| Hermes / VS Code | **Docs only** (v2/v3) | No adapter scripts yet |

**Launcher failure semantics (2026-05):** All three thin launchers use bash `pipefail` (so `tee` does not mask CLI exit codes) and `evaluate_worker_outcome()` — non-trivial result Markdown, JSON file or extracted sidecar, log pattern checks for quota/sandbox errors. Exit non-zero when `ok: false`.

**Shared validation / CI:**

```bash
make validate
python3 scripts/validate_all_adapters.py
./scripts/ci_smoke.sh
```

GitHub Actions: `.github/workflows/validate.yml` on push/PR to `main`.

**Not yet in v1:** Hermes adapter, VS Code extension (embedded panel), automatic worker completion polling (except Cursor `--foreground`).

**v2/v3 (v1 in):** MCP coordinator (`mcp/multi-agent-coordinator/`) and local task panel (`ide/multi-agent-panel/`). See [`docs/roadmap.md`](docs/roadmap.md).

**Honest gap:** Thin adapters launch workers and enforce preflight + post-run artifact checks; they do **not** replace Main accountability for `--sync`, audit, and final delivery. Cursor tmux mode still returns `ok: true` at spawn time only.

## v4 — Tools, memory, benchmark (2026-05)

**Status: v1 in** ✅

| Component | Purpose |
| --- | --- |
| [`tools/`](../tools/) | Stdlib-only git/test/lint/shell/repo-index wrappers with JSON contract |
| [`MEMORY.md`](../MEMORY.md) + [`AGENTS.md`](../AGENTS.md) | Persistent decisions + repo conventions |
| [`memory_log.py`](../adapters/openclaw/scripts/memory_log.py) | Append run summaries; wired into `--summarize` |
| [`bench/`](../bench/) | Local SWE-style cases + `--dry-runtime` harness |
| `tools_used` on task cards | Declarative tool allowlist; audit warnings for gaps |
| MCP `list_framework_tools` | Expose tools/ to MCP clients |
| MCP finding merge | `source: mcp` findings survive `sync_status` |

Self-checks:

```bash
python3 bench/run_bench.py --self-check --dry-runtime
python3 tools/git_tool.py --self-check
python3 adapters/openclaw/scripts/memory_log.py --self-check
python3 adapters/claude-code/scripts/dogfood_claude.py --self-check
```

## v5 — SWE-bench Lite, extensions, multi-language lint (2026-05)

**Status: v1 in** ✅ (scaffolds + offline harness; live LLM runtime optional)

| Component | Purpose | Status |
| --- | --- | --- |
| [`bench/swebench-lite/`](../bench/swebench-lite/) | SWE-bench Lite-shaped multi-file cases + golden patches | ✅ `--self-check` |
| [`examples/case-study-flask-cli/`](../examples/case-study-flask-cli/) | Multi-file stdlib CLI case study | ✅ docs + pytest |
| [`ide/extensions/`](../ide/extensions/) | VS Code / Cursor / Hermes extension scaffolds | ✅ Phase 1 webview only |
| [`memory_rotate.py`](../adapters/openclaw/scripts/memory_rotate.py) | `MEMORY.md` archive + compaction | ✅ wired into `--summarize` |
| MCP finding dedup | `(title, task_id, severity, source)` + content hash | ✅ coordinator + merge |
| [`worker_outcome.py`](../adapters/_shared/worker_outcome.py) | Normalized error vocabulary across runtimes | ✅ fixtures + launchers |
| [`mcp/.../clients/`](../mcp/multi-agent-coordinator/clients/) | Per-client MCP JSON snippets | ✅ |
| [`lint_tool.py`](../tools/lint_tool.py) | eslint, prettier, mypy, pyright, golangci-lint, clippy, rustfmt | ✅ detect-only if absent |
| [`scripts/full_validate.sh`](../scripts/full_validate.sh) | Single “run everything” smoke runner | ✅ |

Self-check:

```bash
bash scripts/full_validate.sh
```

**Honest gaps (v5):**

- Extension scaffolds are not compiled/published; user completes TypeScript build locally.
- SWE-bench Lite harness `--runtime codex|cursor|…` requires external CLIs; default `--self-check` uses golden patches only.
- Hermes remains docs/scaffold — no session launcher yet.
- Live multi-agent on `case-study-flask-cli` requires Codex CLI auth (documented caveat).
