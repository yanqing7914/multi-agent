## Summary

<!-- Explain the user-visible change in 1-3 sentences. -->

## Change Type

- [ ] Bug fix
- [ ] Feature / adapter capability
- [ ] Documentation
- [ ] Gate / audit / safety logic
- [ ] Benchmark / dogfood / CI
- [ ] Release packaging

## Affected Clients

- [ ] Codex App native path
- [ ] Codex CLI bridge
- [ ] Cursor
- [ ] Claude Code
- [ ] OpenClaw / Her
- [ ] Hermes
- [ ] MCP / IDE panel
- [ ] Shared protocol only

## Required Checks

```bash
python3 scripts/validate_all_adapters.py
python3 scripts/verify_release_packages.py --self-check
```

- [ ] Fast validation passes locally or in CI.
- [ ] Full validation is not required, or the reason is documented.
- [ ] No `.codex-multi-agent*/` runtime state is committed.
- [ ] No secrets, tokens, local auth files, or private logs are committed.
- [ ] README / docs / CHANGELOG are updated when behavior changes.

## Codex App Native Review

Required when Codex App behavior changes:

- [ ] `codex-native-plan` still produces `spawn_agent_payload`.
- [ ] Lifecycle is preserved: `spawn_agent -> wait_agent -> optional send_input -> collect reports -> close_agent`.
- [ ] Worker / Reviewer result JSON and Markdown reports are checked.
- [ ] `finalize_native_run.py` blocks missing reports or failed scope audit.
- [ ] `allowed_paths`, `blocked_commands`, and `may_use_skills` are described as scoped prompt/audit constraints, not OS sandbox guarantees.
- [ ] Custom agent files remain installable under `~/.codex/agents`.

## Release Impact

- [ ] No release needed.
- [ ] Release packages must be rebuilt.
- [ ] New tag / GitHub Release needed.

## Linked Issues

Closes #

## Notes

<!-- Breaking changes, follow-ups, known limitations. -->
