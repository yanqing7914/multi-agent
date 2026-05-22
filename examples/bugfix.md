# Bugfix Flow Example

User request: Investigate and fix a failing behavior or test.

Recommended flow:

1. Main collects repro details and environment constraints.
2. Explorer A investigates the failing path.
3. Explorer B investigates adjacent tests or recent changes if useful.
4. Main identifies likely root cause.
5. A single Worker implements the fix within narrow allowed paths.
6. Verifier reruns the failing test and nearby regression tests.
7. Reviewer checks the diff for side effects.
8. Main delivers root cause, fix, validation, and residual risk.

Avoid multiple parallel Workers for bugfixes until root cause is clear.
