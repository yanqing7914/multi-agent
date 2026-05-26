# Feature Flow Example

User request: Add a multi-module feature with tests.

Recommended flow:

1. Main runs Environment Check.
2. Main decides whether Quick Path or Multi-Agent Path applies.
3. Explorer Backend reads API/model/test conventions.
4. Explorer Frontend reads UI/state/request conventions.
5. Main synthesizes an ownership plan.
6. Worker API edits only backend allowed paths.
7. Worker UI edits only frontend allowed paths.
8. Main audits diffs and resolves conflicts.
9. Reviewer reviews the combined diff.
10. Verifier runs targeted tests/build.
11. Main delivers final summary.

Keep Worker task cards disjoint. If API and UI both need shared type changes, assign that shared file to the main agent or a single Worker.
