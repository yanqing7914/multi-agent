# 贡献指南

感谢参与 **multi-agent-coding** 项目。本仓库以协议、脚本与文档为主，请保持变更**可复现、可自测、无密钥**。

## 开发环境

```bash
cd /path/to/multi-agent-coding
python3 -m pip install -e .
```

若 `pip install -e .` 因 PEP 668「externally-managed-environment」失败，请使用虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

亦可直接用系统 `python3` 运行脚本（全部 stdlib，无第三方运行时依赖）。安装包主要用于版本元数据与 CI 对齐。

验证安装（可选）：

```bash
python3 -c "import importlib.metadata as m; print(m.version('multi-agent-coding'))"
```

## 全仓库校验

```bash
make validate
# 或
python3 scripts/validate_all_adapters.py
python3 adapters/openclaw/scripts/validate_all.py
bash scripts/ci_smoke.sh
```

OpenClaw 适配器单独自检：

```bash
cd adapters/openclaw
python3 scripts/validate_all.py
python3 scripts/run_local_demo.py --self-check
```

## 添加客户端适配器

1. 在 `adapters/<client>/` 新建目录：`README.md`、`QUICKSTART.md`、`scripts/` 启动脚本。
2. **复用** OpenClaw 核心：`create_task_cards.py`、`update_task_status.py`、`audit_worker_output.py`（勿复制门控逻辑）。
3. 在 `scripts/run_multi_agent.py` 注册 `--runtime`（见 `adapters/openclaw/scripts/_runtimes.py`）。
4. 更新 `docs/clients.md` 与根 `README.md` 客户端矩阵。
5. 添加 `adapters/<client>/scripts/*_self_check.py` 并挂到 `scripts/validate_all_adapters.py`。

## 添加案例研究

1. 在 `examples/case-study-<name>/` 放置 `README.md`、`task.yaml`（或 JSON）、可选 `app/` / `tests/`。
2. 用 `create_task_cards.py` 生成 `.codex-multi-agent/`（勿提交；已在 `.gitignore`）。
3. 在 `examples/README.md` 增加索引行。
4. 运行 `validate_all.py` 确保无回归。

## 运行基准

```bash
python3 bench/run_bench.py --self-check --dry-runtime
python3 bench/swebench-lite/run_swebench_lite.py --self-check
python3 bench/swebench-lite/run_swebench_lite.py --runtime dry-runtime
```

历史分数：`bench/swebench-lite/results/README.md`。

## 提交 Issue / Pull Request

- **Bug**：使用 [Bug 报告模板](.github/ISSUE_TEMPLATE/bug_report.md)，附复现命令与 `validate_all` 输出。
- **功能**：使用 [功能请求模板](.github/ISSUE_TEMPLATE/feature_request.md)。
- **PR**：填写 [PR 模板](.github/PULL_REQUEST_TEMPLATE.md)；确保 `python3 adapters/openclaw/scripts/validate_all.py` 通过。
- **不要**提交 `.codex-multi-agent*/`、密钥、`.env` 或大段专有代码摘录。

## 文档与门控

- 架构：[`docs/architecture.md`](docs/architecture.md)
- 安全门控注册表：[`docs/safety-rules.md`](docs/safety-rules.md)
- MCP 契约：[`docs/mcp-format.md`](docs/mcp-format.md)

维护者：龚晨昊（[@gongchenhao](https://github.com/gongchenhao)）
