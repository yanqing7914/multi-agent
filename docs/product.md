# Product Definition

`multi-agent` is a productized multi-agent coding entrypoint, not only a prompt collection. Its job is to help a main coding agent split complex work into scoped specialist agents, collect their evidence, audit the resulting diff, and deliver a verified result across Codex, Cursor, Claude Code, OpenClaw, Hermes, and compatible IDE surfaces.

## Product Promise

When a user sends the GitHub link to their agent and says "install this skill", the agent should be able to:

1. Choose the correct client package.
2. Install the native skill entrypoint.
3. Install bundled native Worker / Reviewer agent files when the client supports them.
4. Run a readiness check.
5. Coordinate a real multi-agent task through task cards, result reports, scope audit, and final delivery.

The product does not promise OS-level sandboxing or hard permission isolation. Permissions such as `allowed_paths`, `blocked_commands`, and `may_use_skills` are coordination contracts plus audit gates. The main agent remains accountable.

## Personas

| Persona | Need | Product surface |
| --- | --- | --- |
| App user | "I want Codex/Cursor/Claude App to split work into Workers without me wiring scripts." | Native skill package, quickstart, doctor |
| CLI user | "I want deterministic worker launch from terminal or CI." | `scripts/run_multi_agent.py`, launchers, result reports |
| Maintainer | "I need a source repo that can ship clean packages." | CI, release workflow, package verifier, changelog |
| Reviewer | "I want parallel read-only review with evidence and severity." | Reviewer cards, result reports, findings, final audit |
| Integrator | "I need confidence workers did not touch unrelated files." | ownership, scope audit, worktree tool, finalizer |

## Product Layers

| Layer | Status | Definition of done |
| --- | --- | --- |
| Native skills | In | Client-specific packages install discoverable `SKILL.md` files |
| Native role agents | In for Codex / Claude | Worker and Reviewer definitions installed into client-native agent directories |
| Mission-control state | In | `.codex-multi-agent/` contains tasks, ownership, status, results, audits, summary |
| CLI bridge | In | `run_multi_agent.py` supports supported runtimes and emits auditable reports |
| MCP coordinator | In | Tools expose task state, approvals, findings, path checks, and audits |
| IDE panel | Scaffold | Local panel reads mission-control state; packaged extension publishing remains future work |
| Release packages | In | Build script emits per-client zips plus hashes; verifier checks required product files |
| CI/CD | In | Fast CI, full CI, release workflow, Codex review checklist |
| Branch process | Documented | `feature/* -> dev -> main -> tag` recommended and documented |

## Current Product Shape

The repository ships six installable artifacts:

- `codex-multi-agent-skill-vX.Y.Z.zip`
- `cursor-multi-agent-pack-vX.Y.Z.zip`
- `claude-code-multi-agent-pack-vX.Y.Z.zip`
- `hermes-multi-agent-pack-vX.Y.Z.zip`
- `openclaw-multi-agent-skill-vX.Y.Z.zip`
- `multi-agent-coding-skill-vX.Y.Z.zip`

Client packages are the recommended user-facing product. The generic package is the portable protocol and reference material.

## Quality Gates

Before a release, these commands must pass:

```bash
python3 scripts/validate_all_adapters.py
python3 scripts/build_skill_packages.py --version <version>
python3 scripts/verify_release_packages.py --version <version>
```

For Codex-specific changes, also run:

```bash
python3 adapters/codex/scripts/prepare_native_plan.py --self-check
python3 adapters/codex/scripts/finalize_native_run.py --self-check
python3 adapters/codex/scripts/doctor_codex.py --self-check
```

## Non-Goals

- It is not a real security sandbox.
- It does not bypass each host client's limits, authentication, model quota, or subagent API availability.
- It does not guarantee all App clients expose the same native subagent lifecycle.
- It does not make Worker outputs trustworthy without main-agent review and audit.

## v1.0 Product Bar

The project reaches v1.0 when:

- Release packages install cleanly from GitHub on Codex, Cursor, Claude Code, OpenClaw, and Hermes.
- `doctor.py` gives clear per-client readiness and remediation.
- Codex App native path has documented spawn / wait / result / close lifecycle and custom agents.
- Cursor and Claude have equally direct App usage docs, not only CLI bridge docs.
- Full CI builds and verifies packages on every release tag.
- A public demo shows GitHub-link install, Worker delegation, Reviewer delegation, scope audit, and final delivery.
