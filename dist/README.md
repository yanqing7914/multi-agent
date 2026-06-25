# Skill Downloads

把 GitHub 仓库链接发给你的 agent，并说“安装 multi-agent skill”。agent 应先阅读 `docs/agent-install.md`，再按客户端选择对应安装包。

## v0.3.1

| Package | 用途 | Size | SHA256 |
| --- | --- | ---: | --- |
| [codex-multi-agent-skill-v0.3.1.zip](codex-multi-agent-skill-v0.3.1.zip) | Codex App + CLI 原生 skill；包含 Codex custom agents 与 `codex exec` bridge | 141267 | `2a9dcbda0e63d3d4b8a7712aa74fec362ee6e1fc374caf80124806493041e3fe` |
| [cursor-multi-agent-pack-v0.3.1.zip](cursor-multi-agent-pack-v0.3.1.zip) | Cursor App + CLI 原生 skill；含 headless / `@cursor/sdk` 原生编排与本机 `agent` CLI bridge | 155360 | `c26f761638edec3214e73facb26953af760e67e03e7bb67fc7b4ed237c226588` |
| [claude-code-multi-agent-pack-v0.3.1.zip](claude-code-multi-agent-pack-v0.3.1.zip) | Claude Code App/IDE + CLI 原生 skill；包含 Claude subagents、Agent Teams 映射与 `claude --print` bridge | 141511 | `98472db18f7bc785baffa1cbd240fde196eda30e7ae3e667819de36fdce20c37` |
| [hermes-multi-agent-pack-v0.3.1.zip](hermes-multi-agent-pack-v0.3.1.zip) | Hermes 专用 skill；agentskills.io 可移植 SKILL.md + 原生 MCP（`~/.hermes/config.yaml`） | 135606 | `fc59f2008852165860ad2e2ac8285e1ae58473fecfcee1a12e2a8a274be401a2` |
| [openclaw-multi-agent-skill-v0.3.1.zip](openclaw-multi-agent-skill-v0.3.1.zip) | OpenClaw/Her 专用 skill；包含 mission-control scripts | 76337 | `7b33acdd015fd5c2a2b3f7a071ab841db3fe8f6aaf86e335e7604e54000b2037` |
| [multi-agent-coding-skill-v0.3.1.zip](multi-agent-coding-skill-v0.3.1.zip) | 通用协议包；只包含 skill 规则、模板、清单与 tools/ | 68085 | `bb44176ea07c51536464e12abd8f616bc3e29e0ecf31156eeaf8f3290b993e0a` |

## 安装检查

客户端专用包解压后运行：

```bash
python3 scripts/install_native_skills.py --client all --scope primary --force
python3 scripts/install_native_skills.py --client all --check
```

`multi-agent-coding-skill` 是协议包，不包含原生安装脚本；Codex/Cursor/Claude 用户请优先下载对应客户端包。

## Older Packages

旧版本 zip 保留在本目录中，用于复现历史行为。新安装请使用 v0.3.1。
