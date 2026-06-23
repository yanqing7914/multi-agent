# Skill Downloads

把 GitHub 仓库链接发给你的 agent，并说“安装 multi-agent skill”。agent 应先阅读 `docs/agent-install.md`，再按客户端选择对应安装包。

## v0.3.0

| Package | 用途 | Size | SHA256 |
| --- | --- | ---: | --- |
| [codex-multi-agent-skill-v0.3.0.zip](codex-multi-agent-skill-v0.3.0.zip) | Codex App + CLI 原生 skill；包含 Codex custom agents 与 `codex exec` bridge | 140751 | `2b52c5cd94702930e41e2116a882e4006df877f18f033e557167731f5a561922` |
| [cursor-multi-agent-pack-v0.3.0.zip](cursor-multi-agent-pack-v0.3.0.zip) | Cursor App + CLI 原生 skill；含 headless / `@cursor/sdk` 原生编排与本机 `agent` CLI bridge | 152878 | `81e721222128afb76e8fea4d5c5f6f5bc825da96c4d60a25d1aaa0ca73d87b05` |
| [claude-code-multi-agent-pack-v0.3.0.zip](claude-code-multi-agent-pack-v0.3.0.zip) | Claude Code App/IDE + CLI 原生 skill；包含 Claude subagents、Agent Teams 映射与 `claude --print` bridge | 140993 | `add78a682f67b1aba7eddf208e3dca7b871cc80071c88201f7af8a143105fae1` |
| [hermes-multi-agent-pack-v0.3.0.zip](hermes-multi-agent-pack-v0.3.0.zip) | Hermes 专用 skill；agentskills.io 可移植 SKILL.md + 原生 MCP（`~/.hermes/config.yaml`） | 135090 | `00d98a863f6ade16cd9b761d3e79a24a915d2704b877109d31344d77b82fa5d5` |
| [openclaw-multi-agent-skill-v0.3.0.zip](openclaw-multi-agent-skill-v0.3.0.zip) | OpenClaw/Her 专用 skill；包含 mission-control scripts | 76029 | `4fa9330d2febaded06f3abfb4c72eb5d4c1e807ea7e961ef4b7e9062be7e69c7` |
| [multi-agent-coding-skill-v0.3.0.zip](multi-agent-coding-skill-v0.3.0.zip) | 通用协议包；只包含 skill 规则、模板、清单与 tools/ | 67316 | `9b239346272a46c8e140d0e150c9e2ce72c25d48df1e36b4a6522f713f4a9f98` |

## 安装检查

客户端专用包解压后运行：

```bash
python3 scripts/install_native_skills.py --client all --scope primary --force
python3 scripts/install_native_skills.py --client all --check
```

`multi-agent-coding-skill` 是协议包，不包含原生安装脚本；Codex/Cursor/Claude 用户请优先下载对应客户端包。

## Older Packages

旧版本 zip 保留在本目录中，用于复现历史行为。新安装请使用 v0.3.0。
