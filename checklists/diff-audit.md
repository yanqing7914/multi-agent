# Diff Audit Checklist

Before integration or final delivery:

- Check git status when available.
- Identify user pre-existing changes.
- Identify files changed by each Worker.
- Confirm all Worker changes are within `allowed_paths`.
- Confirm no forbidden paths were read, copied, or modified.
- Check for overlapping Worker edits.
- Check generated files and lockfiles for unintended changes.
- Review test, lint, build, or verification output.
- Record validation not run and why.
- Stop if user changes may be overwritten or conflict resolution is unclear.
