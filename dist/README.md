# Skill Downloads

把 GitHub 仓库链接发给你的 agent，并说“安装 multi-agent skill”。agent 应先阅读 `docs/agent-install.md`，再按客户端选择对应安装包。

## v0.2.0

| Package | 用途 | Size | SHA256 |
| --- | --- | ---: | --- |
| [codex-multi-agent-skill-v0.2.0.zip](codex-multi-agent-skill-v0.2.0.zip) | Codex App + CLI 原生 skill；包含 Codex custom agents 与 `codex exec` bridge | 102019 | `b0986eed46373b5f84722ea8483f1cab52fdf66004cd3df9fd6bcd745f8dd40d` |
| [cursor-multi-agent-pack-v0.2.0.zip](cursor-multi-agent-pack-v0.2.0.zip) | Cursor App + CLI 原生 skill；完整 Worker 自动化通过本机 `agent` CLI bridge | 96332 | `29eb71722f34aa1bfc54e6595b3a94012dc9ce1663716143ebd51ca8561f0af6` |
| [claude-code-multi-agent-pack-v0.2.0.zip](claude-code-multi-agent-pack-v0.2.0.zip) | Claude Code App/IDE + CLI 原生 skill；包含 Claude subagents 与 `claude --print` bridge | 98237 | `d4137ddace728cd41d3adea08febdaffc5da3800280fc738ae4afe49b8340ed5` |
| [openclaw-multi-agent-skill-v0.2.0.zip](openclaw-multi-agent-skill-v0.2.0.zip) | OpenClaw/Her 专用 skill；包含 mission-control scripts | 62162 | `e60c0b0019a7a1fb7bea759d2c620c5cd5c41002c6a8060d3e0b45ce2c5e109a` |
| [multi-agent-coding-skill-v0.2.0.zip](multi-agent-coding-skill-v0.2.0.zip) | 通用协议包；只包含 skill 规则、模板和清单 | 37343 | `e273c282a8ab49d46bab9fd7b058499e9c0a9c02064728d3430635e656d1d839` |

## 安装检查

客户端专用包解压后运行：

```bash
python3 scripts/install_native_skills.py --client all --scope primary --force
python3 scripts/install_native_skills.py --client all --check
```

`multi-agent-coding-skill` 是协议包，不包含原生安装脚本；Codex/Cursor/Claude 用户请优先下载对应客户端包。

## Older Packages

旧版本 zip 保留在本目录中，用于复现历史行为。新安装请使用 v0.2.0。
