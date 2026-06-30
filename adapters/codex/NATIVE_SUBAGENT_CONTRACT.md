# Codex Native Subagent Contract

This contract turns `multi-agent` from guidance into an executable Codex App routine.

## Trigger

Use this contract when the user asks Codex App for multi-agent coding, such as:

- "use multi-agent"
- "open workers/reviewers"
- "spawn several agents"
- "review this with ssrd"
- "split implementation and review"

Do not use it for small single-agent edits.

## Main-Agent Procedure

1. Generate task cards under `.codex-multi-agent/`.
2. Run:

```bash
python scripts/run_multi_agent.py --runtime codex-native-plan --state-dir .codex-multi-agent
```

3. For every `records[]` item in the JSON output, call Codex App native subagent spawn with `record.spawn_agent_payload`:

```text
spawn_agent(**record.spawn_agent_payload)
```

4. Wait for all spawned agents to finish.
5. Require both `record.result_json` and `record.result_markdown`.
6. Run gate sync and scope audit.
7. Deliver only after Main has reviewed subagent output and audit evidence.

## Spawn Record Fields

| Field | Meaning |
| --- | --- |
| `agent_type` | Codex agent type, usually `multi-agent-worker`, `multi-agent-reviewer`, or `explorer` |
| `prompt_path` | Full prompt to send to the native subagent |
| `may_use_skills` | Only skills the subagent may use |
| `result_json` | Required machine-readable result report |
| `result_markdown` | Required human-readable result report |
| `workspace_root` | Expected workspace; subagent must `cd` there first |
| `spawn_agent_payload` | Ready-to-use Codex App spawn payload |

## Role Mapping

| Task role | Agent type | Write policy |
| --- | --- | --- |
| Worker | `multi-agent-worker` | May write only `allowed_paths` |
| Reviewer | `multi-agent-reviewer` | Read-only; may use authorized review skills |
| Explorer | `explorer` | Read-only |
| Verifier | `explorer` | Read-only validation |

## Skill Passing

- If `record.may_use_skills` is empty, do not attach skills.
- If it lists a skill such as `ssrd`, `record.spawn_agent_payload.items` includes a skill item for that skill.
- If the skill is unavailable inside the subagent, the subagent must report `blocked`.
- A skill never expands file, shell, network, credential, git, or role permissions.

## Fallback Order

1. `codex-native-plan`: full Codex App native subagent plan.
2. `codex-native`: single task-card native subagent prompt.
3. `codex`: CLI bridge via `codex exec`.
4. `codex-desktop`: manual prompt handoff.

Never claim native automation if the App does not expose subagent spawning.

## Safety

This is not an OS sandbox. Safety comes from role prompts, custom agent defaults, path ownership, result reports, and Main-agent audit. Main remains responsible for final integration.
