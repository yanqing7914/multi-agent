# Changelog

本文件遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

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

- 许可证尚未在仓库中声明；使用前请与维护者确认。
- Hermes / VS Code 扩展仍为文档与脚手架阶段；实时 LLM bench 运行需各客户端 CLI 与配额。

[0.1.0]: https://github.com/gongchenhao/multi-agent-coding/releases/tag/v0.1.0
