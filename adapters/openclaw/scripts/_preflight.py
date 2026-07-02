"""Shared preflight / anti-false-completion helpers (dependency-free)."""

from __future__ import annotations

import hashlib
from pathlib import Path

READ_ROLES = {"Explorer", "Reviewer", "Verifier"}


def normalize_workspace_path(path: str) -> str:
    return str(Path(path).expanduser().resolve())


def workspace_mismatch_reason(
    result_data: dict,
    expected_workspace: str | None,
    allowed_workspaces: list[str] | None = None,
) -> str | None:
    """Block completed reports when pwd after cd does not match target workspace_root.

    With worktree isolation (default for parallel Workers) the Worker's legitimate
    working directory is its own worktree, so callers pass that path via
    `allowed_workspaces` (from ownership task `worktree.path`).
    """
    reported = str(result_data.get("status", "")).strip()
    if reported != "completed" or not expected_workspace:
        return None
    observed = str(result_data.get("workspace_observed", "")).strip()
    if not observed:
        return None
    candidates = [expected_workspace, *(allowed_workspaces or [])]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            if normalize_workspace_path(observed) == normalize_workspace_path(candidate):
                return None
        except OSError:
            if observed.rstrip("/") == str(candidate).rstrip("/"):
                return None
    return f"workspace_mismatch: observed={observed} expected={expected_workspace}"


def parse_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1"}:
            return True
        if normalized in {"false", "no", "0"}:
            return False
    return None


def normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def path_check_target(pattern: str) -> str:
    """Map a glob like adapters/foo/** to a directory/file to test with os.path.exists."""
    pattern = normalize_path(pattern)
    if pattern.endswith("/**"):
        return pattern[:-3]
    if pattern.endswith("/*"):
        return pattern[:-2]
    if pattern == "**/*":
        return "."
    if "**" in pattern:
        return pattern.split("**")[0].rstrip("/") or "."
    return pattern


def verify_required_paths(workspace_root: Path, required_paths: list[str]) -> tuple[list[str], list[str]]:
    """Return (checked, missing) path patterns relative to workspace_root."""
    checked: list[str] = []
    missing: list[str] = []
    for pattern in required_paths:
        pattern = str(pattern).strip()
        if not pattern or pattern in {"**/*", "**"}:
            continue
        target = path_check_target(pattern)
        full = workspace_root / target
        checked.append(pattern)
        if not full.exists():
            missing.append(pattern)
    return checked, missing


def false_completion_reason(result_data: dict) -> str | None:
    reported = str(result_data.get("status", "")).strip()
    if reported != "completed":
        return None

    verified = parse_bool(result_data.get("required_paths_verified"))
    missing = result_data.get("required_paths_missing", [])
    if not isinstance(missing, list):
        missing = [missing] if missing else []
    missing = [str(item).strip() for item in missing if str(item).strip()]

    if verified is False:
        return "required_paths_verified=false"
    if missing:
        return f"required_paths_missing: {', '.join(missing)}"
    return None


def thin_evidence_reason(result_data: dict, required_paths: list[str] | None = None) -> str | None:
    """Flag completed reports that claim verification but cite no files_read."""
    reported = str(result_data.get("status", "")).strip()
    if reported != "completed":
        return None

    role = str(result_data.get("role", "")).strip()
    if role not in READ_ROLES:
        return None

    verified = parse_bool(result_data.get("required_paths_verified"))
    if verified is not True:
        return None

    paths = required_paths or result_data.get("required_paths_checked") or []
    if not paths or paths == ["**/*"]:
        return None

    concrete = [p for p in paths if str(p).strip() and str(p).strip() not in {"**/*", "**"}]
    if not concrete:
        return None

    files_read = result_data.get("files_read", [])
    if not isinstance(files_read, list):
        files_read = [files_read] if files_read else []
    files_read = [str(item).strip() for item in files_read if str(item).strip()]

    if files_read:
        return None
    return "thin_evidence: required_paths_verified=true but files_read is empty"


def effective_status_issues(
    result_data: dict,
    required_paths: list[str] | None = None,
    expected_workspace: str | None = None,
    allowed_workspaces: list[str] | None = None,
) -> tuple[str | None, dict]:
    """Return effective status override (blocked) and metadata, or (None, {})."""
    mismatch_reason = workspace_mismatch_reason(result_data, expected_workspace, allowed_workspaces)
    false_reason = false_completion_reason(result_data)
    thin_reason = thin_evidence_reason(result_data, required_paths)

    if mismatch_reason:
        return "blocked", {
            "false_completion": True,
            "workspace_mismatch": True,
            "reported_status": result_data.get("status", "completed"),
            "reason": mismatch_reason,
            "workspace_observed": result_data.get("workspace_observed"),
            "expected_workspace": expected_workspace,
        }
    if false_reason:
        return "blocked", {
            "false_completion": True,
            "reported_status": result_data.get("status", "completed"),
            "reason": false_reason,
            "required_paths_verified": parse_bool(result_data.get("required_paths_verified")),
            "required_paths_missing": result_data.get("required_paths_missing", []),
            "workspace_observed": result_data.get("workspace_observed"),
        }
    if thin_reason:
        return "blocked", {
            "false_completion": True,
            "thin_evidence": True,
            "reported_status": result_data.get("status", "completed"),
            "reason": thin_reason,
            "required_paths_verified": parse_bool(result_data.get("required_paths_verified")),
            "files_read": result_data.get("files_read", []),
            "workspace_observed": result_data.get("workspace_observed"),
        }
    return None, {}




def missing_result_report_reason(
    task: dict,
    json_path: Path | None = None,
    md_path: Path | None = None,
) -> str | None:
    """Require JSON result evidence for completed task roles used by gate checks."""
    status = str(task.get("status", "")).strip()
    if status != "completed":
        return None

    role = str(task.get("role", "")).strip()
    if role not in {"Explorer", "Worker", "Reviewer", "Verifier"}:
        return None

    json_exists = bool(json_path and json_path.exists())
    if json_exists:
        return None
    md_exists = bool(md_path and md_path.exists())
    if md_exists:
        return "missing_result_report_json: status=completed cannot pass with Markdown-only result evidence"
    return "missing_result_report_json: status=completed cannot pass without JSON result evidence"

def load_changed_file_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [normalize_path(line.strip()) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def changed_files_digest(lines: list[str]) -> str:
    canonical = "\n".join(sorted(lines))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def changed_files_metadata(path: Path | None) -> dict:
    """Digest/mtime summary for changed-files.txt (used by audit + sync)."""
    if path is None:
        return {
            "changed_files_path": None,
            "changed_files_mtime": None,
            "changed_files_digest": None,
            "changed_files_count": 0,
        }
    resolved = path.resolve()
    if not resolved.exists():
        return {
            "changed_files_path": str(resolved),
            "changed_files_mtime": None,
            "changed_files_digest": None,
            "changed_files_count": 0,
        }
    lines = load_changed_file_lines(resolved)
    stat = resolved.stat()
    return {
        "changed_files_path": str(resolved),
        "changed_files_mtime": stat.st_mtime,
        "changed_files_digest": changed_files_digest(lines),
        "changed_files_count": len(lines),
    }


def audit_stale_reason(state_dir: Path, audit_report: dict, audit_path: Path | None = None) -> str | None:
    """Return a reason string when changed-files.txt is newer or differs from the audit."""
    changed_path = state_dir / "changed-files.txt"
    if not changed_path.exists():
        return None

    audit_digest = audit_report.get("changed_files_digest")
    if audit_digest is None:
        return "audit missing changed_files_digest metadata; rerun audit_worker_output.py --write-audit"

    current = changed_files_metadata(changed_path)
    if current["changed_files_digest"] != audit_digest:
        return "changed-files.txt digest differs from latest audit"

    audit_mtime = audit_report.get("changed_files_mtime")
    if audit_mtime is not None and current["changed_files_mtime"] is not None:
        if current["changed_files_mtime"] > audit_mtime + 1e-6:
            return "changed-files.txt modified after audit inputs were captured"

    if audit_path is not None:
        try:
            if changed_path.stat().st_mtime > audit_path.stat().st_mtime + 1e-6:
                return "changed-files.txt is newer than latest audit file"
        except OSError:
            pass

    generated_at = audit_report.get("generated_at")
    if generated_at and current["changed_files_mtime"] is not None:
        try:
            from datetime import datetime

            audit_ts = datetime.fromisoformat(generated_at.replace("Z", "+00:00")).timestamp()
            if current["changed_files_mtime"] > audit_ts + 1e-6:
                return "changed-files.txt modified after audit was generated"
        except ValueError:
            pass
    return None
