#!/usr/bin/env python3
"""Audit OpenClaw Worker outputs against ownership rules."""

from __future__ import annotations

import argparse
import fnmatch
import json
from pathlib import Path

SECRET_PATTERNS = [
    ".env",
    ".env.*",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "id_rsa",
    "id_ed25519",
]


def normalize(path: str) -> str:
    path = path.replace("\\", "/")
    return path[2:] if path.startswith("./") else path


def matches(path: str, patterns: list[str]) -> bool:
    path = normalize(path)
    for pattern in patterns:
        pattern = normalize(pattern)
        if pattern.startswith("~/"):
            continue
        if fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch("/" + path, pattern):
            return True
    return False


def load_changed_files(path: Path | None) -> list[str]:
    if not path or not path.exists():
        return []
    return [normalize(line.strip()) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def load_result_changes(results_dir: Path | None) -> dict[str, list[str]]:
    changes: dict[str, list[str]] = {}
    if not results_dir or not results_dir.exists():
        return changes
    for result_file in results_dir.glob("*.json"):
        try:
            data = json.loads(result_file.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            continue
        task_id = data.get("task_id") or result_file.stem
        files = [normalize(item) for item in data.get("files_changed", [])]
        changes.setdefault(task_id, []).extend(files)
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ownership", required=True, help="Path to ownership.json")
    parser.add_argument("--results", help="Directory containing JSON result reports")
    parser.add_argument("--changed-files", help="Plain text changed-file list, one path per line")
    args = parser.parse_args()

    ownership_path = Path(args.ownership)
    ownership = json.loads(ownership_path.read_text(encoding="utf-8-sig"))
    tasks = ownership.get("tasks", [])
    task_by_id = {task["task_id"]: task for task in tasks}

    result_changes = load_result_changes(Path(args.results) if args.results else None)
    global_changed = load_changed_files(Path(args.changed_files) if args.changed_files else None)

    violations = []
    warnings = []
    touched_by_path: dict[str, list[str]] = {}

    for task_id, files in result_changes.items():
        task = task_by_id.get(task_id)
        if not task:
            warnings.append({"task_id": task_id, "reason": "Result has no matching ownership task"})
            continue
        if task.get("role") != "Worker":
            if files:
                violations.append({"task_id": task_id, "reason": "Non-Worker reported changed files", "files": files})
            continue
        allowed = task.get("allowed_paths", [])
        blocked = task.get("blocked_paths", []) + SECRET_PATTERNS
        for file_path in files:
            touched_by_path.setdefault(file_path, []).append(task_id)
            if matches(file_path, blocked):
                violations.append({"task_id": task_id, "path": file_path, "reason": "Matches blocked/secret path"})
            elif not matches(file_path, allowed):
                violations.append({"task_id": task_id, "path": file_path, "reason": "Outside allowed_paths"})

    if global_changed:
        worker_allowed = [task for task in tasks if task.get("role") == "Worker"]
        for file_path in global_changed:
            if matches(file_path, SECRET_PATTERNS):
                violations.append({"path": file_path, "reason": "Changed file looks like a secret path"})
            owners = [task["task_id"] for task in worker_allowed if matches(file_path, task.get("allowed_paths", []))]
            if not owners:
                warnings.append({"path": file_path, "reason": "Changed file is not owned by any Worker"})
            elif len(owners) > 1:
                warnings.append({"path": file_path, "reason": "Changed file matches multiple Worker ownership scopes", "tasks": owners})

    conflicts = [
        {"path": path, "tasks": ids, "reason": "Multiple Workers reported same changed file"}
        for path, ids in touched_by_path.items()
        if len(set(ids)) > 1
    ]

    missing_results = [
        task["task_id"]
        for task in tasks
        if task.get("role") == "Worker" and task["task_id"] not in result_changes
    ]
    for task_id in missing_results:
        warnings.append({"task_id": task_id, "reason": "Worker result report not found"})

    ok = not violations and not conflicts
    report = {"ok": ok, "violations": violations, "conflicts": conflicts, "warnings": warnings}
    print(json.dumps(report, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())


