# multi-agent-coding

A prompt-guided Codex skill for coordinating multi-agent coding work with scoped roles, task cards, review passes, verification, and final delivery rules.

## What it does

- Decides when multi-agent coordination is useful and when to stay single-agent.
- Defines Main, Explorer, Worker, Reviewer, Verifier, and Integrator roles.
- Provides task-card, result-report, and final-delivery templates.
- Controls Worker skill use through explicit task-card permissions.
- Supports multi-reviewer workflows, including review skills such as `ssrd`.
- Adds safety, workspace hygiene, and diff-audit checklists.

## Important note

This skill is a coordination protocol, not a sandbox or orchestrator. It guides Codex behavior but does not enforce filesystem, network, git, or process isolation by itself.

## Structure

```text
SKILL.md
agents/openai.yaml
templates/
checklists/
examples/
```

## Usage

Install or copy this folder into a Codex skills directory, then invoke it explicitly:

```text
Use $multi-agent-coding to coordinate this coding task with scoped roles, review, and verification.
```

Typical triggers:

- Use multiple agents to review this plan.
- Open reviewers with `ssrd` to assess this diff.
- Split this feature into Explorer, Worker, Reviewer, and Verifier roles.
- Decide whether this task is worth multi-agent coordination.
