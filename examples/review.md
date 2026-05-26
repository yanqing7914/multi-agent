# Review Flow Example

User request: Open multiple agents to review a plan, code diff, document, or design.

Recommended flow:

1. Main enters Review Mode.
2. Main creates 2-4 Reviewer task cards with distinct focus areas.
3. Each Reviewer is read-only and has `write_permission: false`.
4. If the user names a review skill such as `ssrd`, add it to `may_use_skills` for each Reviewer.
5. Reviewers output findings by severity with evidence.
6. Main merges duplicate findings, separates confirmed issues from opinions, and summarizes consensus/divergence.

Example Reviewer focuses:

- Correctness and missing requirements.
- Security and permission risks.
- Maintainability and implementation cost.
- User experience and edge cases.

Reviewer prompt rule:

```text
Use the ssrd skill to review the target. Read only. Do not modify files. Do not spawn subagents. Output actionable findings by severity.
```
