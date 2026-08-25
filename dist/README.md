# Skill Downloads

把 GitHub 仓库链接发给你的 agent，并说“安装 multi-agent skill”。agent 应先阅读 `docs/agent-install.md`，再按客户端选择对应安装包。

## v0.4.0

| Package | 用途 | Size | SHA256 |
| --- | --- | ---: | --- |
| [codex-multi-agent-skill-v0.4.0.zip](codex-multi-agent-skill-v0.4.0.zip) | Codex App + CLI 原生 skill；包含 Codex custom agents 与 `codex exec` bridge | 165979 | `96b19c6f45b076eb57fdc011a4d23c78c3273817c56aa250884d48dc9e241f34` |
| [cursor-multi-agent-pack-v0.4.0.zip](cursor-multi-agent-pack-v0.4.0.zip) | Cursor App + CLI 原生 skill；含 headless / `@cursor/sdk` 原生编排与本机 `agent` CLI bridge | 163272 | `a87001a6217378e722b00ba4c28e0470069b0642ae31e527b52636e93cb39d87` |
| [claude-code-multi-agent-pack-v0.4.0.zip](claude-code-multi-agent-pack-v0.4.0.zip) | Claude Code App/IDE + CLI 原生 skill；包含 Claude subagents、Agent Teams 映射与 `claude --print` bridge | 149208 | `a928a482c39e7435737606f856058c7f064baca8ed8e452ec8d7b909f21dc9a0` |
| [hermes-multi-agent-pack-v0.4.0.zip](hermes-multi-agent-pack-v0.4.0.zip) | Hermes 专用 skill；agentskills.io 可移植 SKILL.md + 原生 MCP（`~/.hermes/config.yaml`） | 143331 | `d0ff4b3157813eda467ae07f0615c638f497e38645eadc02c574a29e89792675` |
| [openclaw-multi-agent-skill-v0.4.0.zip](openclaw-multi-agent-skill-v0.4.0.zip) | OpenClaw/Her 专用 skill；包含 mission-control scripts 与 worktree 工具 | 99403 | `db9f6286d2fa5c96a47f1e8a00b2c8b060d5553a4c01e79f220e830a98b7422f` |
| [multi-agent-coding-skill-v0.4.0.zip](multi-agent-coding-skill-v0.4.0.zip) | 通用协议包；只包含 skill 规则、模板、清单与 tools/ | 75486 | `d9b526f438fdd5ab026bdc945e9cce3c738ec2e7d0a6c78c6ccd5503572296ce` |

## 安装检查

客户端专用包解压后运行：

```bash
python3 scripts/install_native_skills.py --client all --scope primary --force
python3 scripts/install_native_skills.py --client all --check
```

`multi-agent-coding-skill` 是协议包，不包含原生安装脚本；Codex/Cursor/Claude 用户请优先下载对应客户端包。

旧版本包不再跟踪在仓库中；历史版本请从对应的 GitHub Release 获取。
