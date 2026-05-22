# Should Use Multi-Agent Checklist

Use multi-agent-coding when one or more are true:

- User explicitly asks for multiple agents, subagents, parallel workers, reviewers, or agent collaboration.
- Task spans multiple independent modules or layers.
- Task needs separate research, implementation, review, and verification passes.
- Codebase is large enough that parallel Explorer passes reduce risk.
- User asks for multi-perspective review, security review, architecture review, or deep investigation.
- Risk is high enough to justify an independent Reviewer.

Prefer Quick Path when:

- Single-file or obvious small change.
- Bug root cause is already known.
- Work has no safe ownership split.
- Requirements are unclear and need user clarification first.
- Multiple Workers would modify the same files.
- Added coordination would cost more than it saves.

Decision:

- Small task: Quick Path.
- Medium task: Main + optional Explorer + Worker + Reviewer.
- Large task: Main + 1-3 Explorers + 1-2 Workers + Reviewer + Verifier.
- Very large task: consider worktree/tooling beyond v0.1.
