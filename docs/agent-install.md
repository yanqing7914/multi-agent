# Agent Install Guide

This page is written for AI agents. If a user gives you this GitHub repository and says "install this skill", choose the package that matches your client.

Repository: `https://github.com/yanqing7914/multi-agent`

## Choose Package

| Client | Download | Install action |
| --- | --- | --- |
| Codex | `codex-multi-agent-skill-v0.1.4.zip` | Extract `codex-multi-agent/` into the user's Codex skills directory. Prefer native Codex Desktop subagents; handoff and Codex CLI are fallbacks. |
| OpenClaw / Her | `openclaw-multi-agent-skill-v0.1.4.zip` | Extract the top-level `openclaw-multi-agent/` folder into the OpenClaw skills directory. |
| Cursor | `cursor-multi-agent-pack-v0.1.4.zip` | Extract anywhere stable, then add `cursor-rules.md` or `.cursor/rules/multi-agent-coding.mdc` to the target workspace rules. Desktop users can use `--runtime cursor-desktop`; CLI users can use `--runtime cursor`. |
| Claude | `claude-code-multi-agent-pack-v0.1.4.zip` | Extract anywhere stable, then use `CLAUDE.md` for Claude Code or `--runtime claude-desktop` for Claude Desktop / Claude.ai custom-skill prompts. |
| Generic agent | `multi-agent-coding-skill-v0.1.4.zip` | Extract and read `SKILL.md`; this is protocol guidance only, not a launcher pack. |

## Codex Install

1. Download the Codex package from the latest GitHub Release.
2. Extract it.
3. Move `codex-multi-agent/` to:

```text
~/.codex/skills/codex-multi-agent
```

4. Restart Codex.
5. Use `$codex-multi-agent` for client-specific execution, or `$multi-agent-coding` for protocol-only guidance.

Codex Desktop users can arrange Workers without Codex CLI. Prefer native Desktop subagents when the app exposes them:

```bash
python3 ~/.codex/skills/codex-multi-agent/scripts/run_multi_agent.py \
  --runtime codex-native \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Main reads the returned `prompt_path` and spawns a native Codex subagent with the returned `agent_type`. If native subagent tools are unavailable, use `--runtime codex-desktop` to generate a manual handoff prompt. If Codex CLI is installed, use `--runtime codex` for automatic `codex exec` worker launch.

## Cursor Install

1. Download `cursor-multi-agent-pack-v0.1.4.zip`.
2. Extract it into a stable local directory, for example:

```text
~/agent-packs/cursor-multi-agent
```

3. In the target project, add either:

```text
.cursor/rules/multi-agent-coding.mdc
```

or merge `cursor-rules.md` into the project's Cursor rules.

4. For Cursor Desktop prompt mode:

```bash
python3 ~/agent-packs/cursor-multi-agent/scripts/run_multi_agent.py \
  --runtime cursor-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Open or paste the returned `prompt_path` in Cursor Agent. For automatic workers, ensure `agent`, `tmux`, `python3`, and `bash` are available and use `--runtime cursor`.

## Claude Install

1. Download `claude-code-multi-agent-pack-v0.1.4.zip`.
2. Extract it into a stable local directory, for example:

```text
~/agent-packs/claude-code-multi-agent
```

3. Merge the bundled `CLAUDE.md` into the target project's `CLAUDE.md`, or tell Claude Code to read it before coordinating multi-agent tasks.
4. For Claude Desktop / Claude.ai prompt mode:

```bash
python3 ~/agent-packs/claude-code-multi-agent/scripts/run_multi_agent.py \
  --runtime claude-desktop \
  --task-card .codex-multi-agent/tasks/T002-worker-backend.md
```

Use the returned `prompt_path` in Claude Desktop / Claude.ai custom skill context. For automatic local workers, ensure `claude`, `python3`, and `bash` are available and use `--runtime claude-code`. Inside OpenClaw, prefer ACP handoff.

## Smoke Test

From the extracted package root:

```bash
python3 scripts/run_multi_agent.py --help
python3 adapters/openclaw/scripts/validate_all.py
```

For client-specific checks:

```bash
python3 adapters/codex/scripts/codex_self_check.py
python3 adapters/cursor/scripts/cursor_self_check.py
python3 adapters/claude-code/scripts/claude_code_self_check.py
```

Only run the check that matches the package/client you installed.
