# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.4.0] - 2026-07-02

### Fixed

- **worktree 隔离下的 workspace 误报（dogfood 发现）**：默认 worktree 隔离落地后，Worker 的 `workspace_observed` 合法地指向自己的 worktree 路径，但 `_preflight.workspace_mismatch_reason` 只认主 `workspace_root`，导致审计/同步把所有隔离 Worker 判为 workspace mismatch 违规——即默认隔离必然过不了自己的审计门。现在 `audit_worker_output.py` 与 `update_task_status.py --sync` 会把 ownership 任务里的 `worktree.path` 视为合法工作目录（其他路径仍然违规），并新增 pytest 回归。该缺陷是在用本 skill 真实编排一次双 Worker 文档更新（Cursor App 内 spawn Explorer×2 / Worker×2 / Reviewer，worktree 隔离 + capture + audit + merge 全流程）时由审计门自己拦出来的。
- **堵住 scope 审计盲区（安全修复）**：此前 changed-files 用 `git diff --name-only` 捕获，不包含 untracked 新文件——Worker 在 `allowed_paths` 之外**新建**文件时审计完全看不到。新增 `adapters/openclaw/scripts/capture_changed_files.py`（staged + unstaged + untracked 的并集，自动排除 state 目录，带 `--self-check`），并把任务卡 `after_result`、`finalize_native_run.py`、run-plan、audit 提示语以及全部 adapter 文档（cursor/codex/hermes/openclaw QUICKSTART、SKILL、README、TEAMS、SDK、examples）切换到新命令。发布包校验新增该脚本为 codex/cursor/openclaw 包的必备文件。
- **自检不再污染仓库**：`run_local_demo.py`（被 `validate_all_adapters.py` 间接调用）以前默认把 REPO_ROOT 当 workspace，`--summarize` 每次都会往仓库跟踪的 `MEMORY.md` 追加一行 dogfood 记录，导致每跑一次验证工作区就脏一次。demo/self-check 现在默认使用一次性临时 workspace。
- **Windows PowerShell 兼容**：任务卡 `preflight_command` 由 `cd "<root>" && pwd` 拆分为两条独立命令（旧版 PowerShell 不支持 `&&`）；同步修正 `prepare_cursor_sdk.py` 与 `templates/task-card.md`。
- 修复 `pyproject.toml` 带 UTF-8 BOM 导致 `pip install -e .` 直接解析失败的问题。

- **修复并行 Worker 状态竞态**：多个 `update_task_status.py` 进程并发更新 `ownership.json` / `status.json` 时是整文档的 read-modify-write，后写者会静默丢弃先写者的更新。新增 `adapters/openclaw/scripts/_locking.py`（msvcrt/fcntl 跨平台建议锁 + 临时文件原子替换写入），`update_task_status.py` 的全部 CLI 变更入口与 `audit_worker_output.py --write-audit` 均在 state 目录锁内执行；JSON 写入改为原子替换，读者不会再读到半截文件。

### Added

- **pip/PyPI 分发就绪**：新增 `multi_agent_coding` 包与 `multi-agent-coding` 控制台命令（hatchling 构建，`force-include` 把整棵技能树打进 wheel 的 `_bundle/`，仓库内仍是单一事实来源）。子命令 `doctor / install / cards / status / capture / audit / worktree / run` 一一转发到打包脚本，源码 checkout 与 pip 安装两种形态都能解析技能树；`self-check` 与 `path` 用于验证与定位。已在干净 venv 里完成 wheel 安装 + `cards/doctor/capture --self-check` 端到端验证。新增 `release-pypi.yml`（tag 触发，PyPI Trusted Publishing，含 tag/版本一致性检查与 wheel 冒烟测试）——发布前需在 pypi.org 侧配置一次 GitHub 可信发布者。`pip-cli` 自检接入 `validate_all_adapters.py`，pytest 新增 4 例 CLI 回归。
- **并行 Worker 的 git worktree 物理隔离改为默认开启**：`create_task_cards.py` 检测到 2 个及以上有写权限的 Worker 时（`--worktrees auto`，默认值），自动生成 `worktree-plan.json`，每张 Worker 卡带 `worktree:` 块（分支、路径、create/capture/merge/remove 完整命令，基于 `tools/worktree_tool.py`）；卡片的 preflight/before_spawn/after_result 自动改指各自的 worktree 路径，ownership.json 与 run-plan.json 同步记录分支与合并指引。单 Worker 无并行覆写风险则自动跳过，`--worktrees off` 可显式关闭、`always` 强制开启。openclaw 独立包现在随包携带 `tools/`（worktree_tool 及其依赖），三个发布包校验将 `tools/worktree_tool.py` 列为必备文件。新增 pytest 回归（默认出计划/off 关闭/单 Worker 跳过）与 self-check 断言，SKILL.md（根、openclaw、cursor）同步更新默认策略。
- 新增 `tests/` 核心脚本单元测试（pytest，10 例）：覆盖审计盲区回归（untracked 越界文件必须 fail strict 审计）、越界 files_changed 拒绝、任务卡不含 `&&`、发布包 forbidden 匹配规则、**多进程并发更新任务状态不丢更新**等，并接入 `ci-fast`、`ci-full` 与 `make test`。
- `validate_all_adapters.py` 并行执行自检（`--jobs`，默认 min(8, CPU)），带 `[n/total]` 进度和每项耗时；本机实测从约 5 分钟降至约 1 分钟。所有自检均为临时目录内的封闭操作，可安全并行。

### Changed

- `release-pypi.yml` 的 publish 作业改为受仓库变量 `PYPI_TRUSTED_PUBLISHING=enabled` 门控：在 pypi.org 配置好 Trusted Publisher 之前，打 tag 只构建并冒烟验证 wheel/sdist（产物存为 artifact），不会因发布失败挂红。配置完成后设置该变量即可自动发布。

## [0.3.1] - 2026-06-25

### Fixed

- **Cursor App could not dispatch a Worker.** The Cursor skill framed the only automatic-Worker path as the external `agent` CLI bridge (which needs `agent` + tmux), and never told the Cursor Main agent it can dispatch Workers by spawning Cursor subagents directly (in-App delegation, no external CLI). Reworked `adapters/cursor/SKILL.md` to make **in-App subagent delegation the primary path** (with a concrete "How To Dispatch A Worker In Cursor App" section), demoting the `agent` CLI bridge to an optional scripted/CI path. Updated `install_native_skills.py` readiness (`worker_bridge_ready`/`readiness_note`) and `doctor.py` verdict so Cursor is reported **ready once the skill is installed** (the `agent` CLI is optional), instead of the misleading "automatic Worker needs the local Cursor CLI".
- Propagated the corrected Cursor model across all docs (`adapters/cursor/README.md`, `QUICKSTART.md`, `docs/clients.md`, `docs/agent-install.md`, root `README.md`, and the packaged `.cursor/rules` generator in `build_skill_packages.py`) so no document still presents the `agent` CLI bridge as Cursor's primary/required automation path.
- Fixed a flaky `update_task_status.py --self-check` (the "scope_audit gate must stay pending when audit has warnings" assertion). Three audit fixtures written within one clock tick could tie on mtime, so `load_latest_audit` non-deterministically picked the wrong "latest" audit under load. The self-check now stamps strictly increasing (future) mtimes on its audit fixtures, making latest-audit selection deterministic without changing product behavior.

## [0.3.0] - 2026-06-23

### Added

- Added `scripts/doctor.py`: a friendly, dependency-free readiness report. Per client it checks native skill install, bundled native agent files, App/CLI tooling (CLI on PATH + best-effort config detection), and complete Worker readiness, then prints Chinese "下一步" remediation hints. Supports `--client`, `--json`, and a deterministic `--self-check`.
- Bundled `doctor.py` into client packages (`SHARED_ITEMS`) and wired `doctor.py --self-check` into `scripts/validate_all_adapters.py`.
- Added `tools/worktree_tool.py`: dependency-free git worktree helper that adds physical isolation for parallel Workers (industry practice from Cursor Agents / Claude Code worktrees). Supports `create`/`list`/`remove` and `plan` straight from `ownership.json` (one isolated worktree + `multi-agent/<task>-<session>` branch per write-permitted Worker), plus a deterministic `--self-check` wired into `scripts/validate_all_adapters.py`. Worktrees default to a `<repo>.worktrees/` sibling so they never pollute the main tree's `git status` / scope audit.
- Added a **Hermes** adapter (`adapters/hermes/`): portable agentskills.io `SKILL.md` skill + native-MCP integration (`~/.hermes/config.yaml`), reusing the OpenClaw mission-control scripts for task cards and scope audit. Registered across `install_native_skills.py` (client `hermes`), `build_skill_packages.py` (`hermes-multi-agent-pack`), `run_multi_agent.py` (`--runtime hermes`), `configure_mcp.py`, `doctor.py`, and `validate_all_adapters.py`.
- Added a **loop engineering** engine (`adapters/openclaw/scripts/run_loop.py`): a bounded, verifier-gated, self-correcting loop (Goal / Actions / independent Verify with maker≠checker / Repair / Memory / bounded stop). CLI maker calls `run_multi_agent.py`; verifier runs a `--verify-command` and can AND in `audit_worker_output.py`. Documented as a first-class path in `SKILL.md`.
- Added Cursor native orchestration paths: `adapters/cursor/scripts/prepare_cursor_sdk.py` (headless `agent -p --output-format json` commands + SDK run-spec from `ownership.json`), `adapters/cursor/sdk/` (`@cursor/sdk` reference orchestrator), and `adapters/cursor/SDK.md`.
- Added `scripts/configure_mcp.py`: one-step MCP registration for Cursor/Claude (JSON merge), Codex (TOML block), and Hermes (YAML block); defaults to `--dry-run`.
- Added `mcp/multi-agent-coordinator/scripts/serve.py` and strengthened the MCP `self_check.py` to cover all 14 tools / 4 resources / 4 prompts; added a Hermes MCP config template.
- Bundled the whole `tools/` directory into client and generic packages.
- Added runtime dependency **auto-unblock**: `create_task_cards.py` now persists the static dependency graph (`dependencies`) onto each `ownership.json` task, and `update_task_status.py --sync` derives per-task `dependencies` / `blocked_by` / `ready_to_spawn` in `status.json` (and shows `[blocked_by: …]` / `[ready_to_spawn]` in the run summary). Added `update_task_status.py --ready` to print the ready-to-spawn / blocked task lists for Main and loops. This is additive and does not change gate pass/fail semantics. Added `ide/multi-agent-panel/scripts/open_panel.py` one-command launcher (auto free port, browser open, `--self-check`).
- Exposed `plan_worktrees` (git worktree isolation) and `check_readiness` (doctor) as MCP coordinator tools so Cursor/Claude/Codex/Hermes can drive worktree isolation and readiness checks natively.
- Added `adapters/openclaw/scripts/run_graph.py`: a dependency-ordered scheduler that operationalizes auto-unblock — it repeatedly syncs, finds `ready_to_spawn` tasks, dispatches each via `run_multi_agent.py`, and re-evaluates until the graph completes, deadlocks, or hits a bounded `--max-rounds`. Injectable `schedule_graph(state_dir, dispatch, max_rounds=...)` core, deterministic `--self-check`, and a safe dry-plan default (`--execute` to actually launch).

- Cursor bridge detection now accepts either `agent` (current) or `cursor-agent` (legacy alias); readiness uses any-of semantics via a new `worker_bridge_ready` helper in `install_native_skills.py`.
- `launch_cursor_worker.py` resolves the Cursor CLI binary at runtime (`agent` → `cursor-agent` fallback) inside the login shell, so the bridge works regardless of which alias is installed.
- Documented accurate Cursor CLI install commands (macOS/Linux/WSL `curl` installer and native Windows PowerShell `irm` installer), the `~/.local/bin` PATH step, and the `bash`/`tmux` (WSL) requirement across the Cursor adapter docs, `docs/clients.md`, `docs/agent-install.md`, and root `README.md`.
- Corrected the outdated "Cursor has no native subagent API" narrative across the Cursor adapter docs, `docs/clients.md`, `docs/agent-install.md`, `SKILL.md`, and `README.md` to reflect Cursor 3 (Agents Window, `/multitask`, `/worktree`, `@cursor/sdk`), while keeping the `agent` CLI bridge as the deterministic scripted path.
- Added a `--runtime hermes` branch to `run_multi_agent.py` and `hermes` to the shared runtime choices.

### Fixed

- `build_skill_packages.py` did not bundle `scripts/doctor.py` into client packages even though the changelog and `docs/agent-install.md` smoke test referenced it; client packages now include `doctor.py` and the `tools/` directory.
- `adapters/codex/scripts/prepare_native_subagent.py` mapped the Reviewer role to the built-in `explorer` agent type, losing the OS-level read-only sandbox defined in `multi-agent-reviewer.toml`; Worker now maps to `multi-agent-worker` and Reviewer to `multi-agent-reviewer` (Explorer/Verifier keep built-in read-only `explorer`). Documented that reliable custom `agent_type` selection needs Codex CLI >= 0.139.0.

## [0.2.0] - 2026-06-17

### Added

- Added native installer `scripts/install_native_skills.py` for Codex, Cursor, and Claude Code packages.
- Added Codex custom agent definitions under `adapters/codex/agents/`.
- Added Claude Code subagent definitions under `adapters/claude-code/agents/`.
- Added v0.2 client support model for App and CLI surfaces.

### Changed

- Reframed Codex App/CLI as native skill + native subagent first, with `codex exec` as optional bridge.
- Reframed Cursor App/CLI as native Agent Skill plus local `agent` CLI bridge for complete Worker automation.
- Reframed Claude Code App/IDE/CLI as native skill + bundled subagents first, with `claude --print` as optional bridge.
- Updated GitHub-link install docs so another agent can install the correct package directly from the repository link.

### Fixed

- Client packages now include the native installer and only the adapter assets needed by that client.
- Validation now includes native installer self-checks.

## [0.1.5] - 2026-06-17

### Fixed

- Updated GitHub-link install docs and demo references from v0.1.4/v0.1.3 to v0.1.5.
- Documented `cursor-desktop` and `claude-desktop` in the launcher example.

## [0.1.4] - 2026-06-17

### Added

- Cursor Desktop prompt mode via `--runtime cursor-desktop`.
- Claude Desktop / Claude.ai prompt mode via `--runtime claude-desktop`.
- Shared Desktop prompt helper for non-native Desktop surfaces.
- End-to-end GitHub-link install demo under `examples/end-to-end-agent-install/`.

### Changed

- Cursor docs now describe Desktop prompt/rules mode and CLI/tmux mode separately.
- Claude docs now separate Desktop/custom-skill prompt, Claude Code CLI, and OpenClaw ACP paths.
- Client packages include updated Desktop guidance and prompt-generation scripts.

## [0.1.3] - 2026-06-08

### Added

- Codex Desktop native subagent mode via `--runtime codex-native`.
- `adapters/codex/scripts/prepare_native_subagent.py` to produce spawn-ready task-card prompts for native Desktop subagents.

### Changed

- Codex adapter is now native-subagent-first, with Desktop handoff and `codex exec` as fallbacks.
- Codex docs now explain skill routing for review skills such as `ssrd` inside spawned Reviewers.

## [0.1.2] - 2026-06-08

### Added

- `docs/agent-install.md`：面向 AI agent 的安装入口，支持用户直接发送 GitHub 链接并要求安装 skill。
- `scripts/build_skill_packages.py`：生成 Codex、Cursor、Claude Code、OpenClaw 与通用协议包。
- v0.1.2 客户端专用包：`codex-multi-agent-skill`、`cursor-multi-agent-pack`、`claude-code-multi-agent-pack`。
- Codex Desktop handoff：无 Codex CLI 时可生成 Worker prompt，由 Desktop Main 安排 Worker 会话写回 result report。

### Changed

- README 下载区改为客户端矩阵，明确 Codex / Cursor / Claude Code / OpenClaw 的不同安装动作。
- 根 `SKILL.md` 增加安装分流说明，避免 agent 只安装通用协议包却缺少 launcher 依赖。

## [0.1.1] - 2026-05-28

### Added

- `BENCHMARKS.md`：汇总 SWE-bench Lite-shaped 历史归档，区分 latest/best runtime 结果。
- `bench/swebench-lite/results/latest-summary.json`：机器可读最新跑分摘要。
- v0.1.1 skill 下载包：`openclaw-multi-agent-skill-v0.1.1.zip` 与 `multi-agent-coding-skill-v0.1.1.zip`。

### Changed

- `run_swebench_lite.py` 新增 `--timeout` 与 `SWEBENCH_LITE_TIMEOUT`；Codex live run 默认 timeout 从 300s 提升到 900s。
- README 下载链接更新到 v0.1.1 release assets。

### Fixed

- 明确 Codex 最新 0/3 跑分的直接原因是 launcher timeout；保留早期 Codex `api-pagination` 成功样本作为对照。
- 清理 v0.1.0 文档/metadata 的历史不一致问题。
## [0.1.0] - 2026-05-26

### Added

- **multi-agent-coding Skill**（`SKILL.md`、`agents/openai.yaml`）：多角色协作流程、任务卡/结果报告模板、权限与安全检查清单。
- **OpenClaw v1 适配器**（`adapters/openclaw/`）：`create_task_cards.py`、`update_task_status.py`、`audit_worker_output.py`、`verify_workspace.py`、`run_local_demo.py`、`validate_all.py`；本地 `.codex-multi-agent/` 任务控制状态。
- **跨客户端薄适配层**：Cursor、Codex、Claude Code（`adapters/cursor/`、`adapters/codex/`、`adapters/claude-code/`）与统一启动器 `scripts/run_multi_agent.py`。
- **MCP 协调服务**（`mcp/multi-agent-coordinator/`）：任务/门控/审计状态的 stdio MCP 实现。
- **IDE 任务面板**（`ide/multi-agent-panel/`）：本地 Web UI 脚手架。
- **工具层**（`tools/`）：`git_tool`、`test_runner_tool`、`lint_tool`、`shell_tool`、`repo_index_tool`（stdlib，JSON 入出）。
- **记忆层**：`MEMORY.md`、`memory_log.py`、`memory_rotate.py`；`--summarize` 自动追加运行摘要。
- **基准 harness**：`bench/run_bench.py`；**SWE-bench Lite 形态**离线用例（`bench/swebench-lite/`）。
- **案例研究**：FizzBuzz 全门控绿路径（`examples/case-study-fizzbuzz/`）；多文件 Flask 形态 CLI（`examples/case-study-flask-cli/`）。
- **文档**：`docs/clients.md`、`docs/mcp-format.md`、`docs/roadmap.md`；`AGENTS.md` 仓库级角色约定。
- **反虚假完成门控**：`false_completion`、`thin_evidence`、`workspace_mismatch`、`stale_audit`、`missing_result_report_json`、`invalid_status_token`、`mission_control_exempt`、`undeclared_tool_used` / `missing_tools_used`。
- **`workspace_root` 轴心**：任务卡强制绝对工作区路径与 `verify_workspace.py` 预检。
- **审计语义修正**：`audit_worker_output.py` 仅在 `gate.status=passed` 时 `ok=true`；`changed-files.txt` 摘要漂移触发 stale audit。

### Changed

- 根 `README.md` 中文说明与客户端矩阵；OpenClaw `QUICKSTART.md` Golden Path。
- `.gitignore` 合并 `.codex-multi-agent*/` 变体目录。

### Notes

- 许可证：MIT。
- Hermes / VS Code 扩展仍为文档与脚手架阶段；实时 LLM bench 运行需各客户端 CLI 与配额。

[0.4.0]: https://github.com/yanqing7914/multi-agent/releases/tag/v0.4.0
[0.3.1]: https://github.com/yanqing7914/multi-agent/releases/tag/v0.3.1
[0.3.0]: https://github.com/yanqing7914/multi-agent/releases/tag/v0.3.0
[0.2.0]: https://github.com/yanqing7914/multi-agent/releases/tag/v0.2.0
[0.1.5]: https://github.com/yanqing7914/multi-agent/releases/tag/v0.1.5
[0.1.4]: https://github.com/yanqing7914/multi-agent/releases/tag/v0.1.4
[0.1.3]: https://github.com/yanqing7914/multi-agent/releases/tag/v0.1.3
[0.1.2]: https://github.com/yanqing7914/multi-agent/releases/tag/v0.1.2
[0.1.1]: https://github.com/yanqing7914/multi-agent/releases/tag/v0.1.1
[0.1.0]: https://github.com/yanqing7914/multi-agent/releases/tag/v0.1.0
