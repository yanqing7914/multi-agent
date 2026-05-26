#!/usr/bin/env python3
"""Post-run worker outcome checks (dependency-free)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

MIN_RESULT_MD_BYTES = 64

# Normalized cross-runtime error vocabulary
NORMALIZED_ERROR_CODES = frozenset(
    {
        "quota_exhausted",
        "sandbox_readonly",
        "auth_required",
        "network_unavailable",
        "tool_missing",
        "timeout",
    }
)

# Legacy / raw patterns mapped to normalized codes
ERROR_PATTERN_GROUPS: list[tuple[str, list[re.Pattern[str]]]] = [
    (
        "quota_exhausted",
        [
            re.compile(r"\b429\b"),
            re.compile(r"\bbudget\b", re.IGNORECASE),
            re.compile(r"\bquota\b", re.IGNORECASE),
            re.compile(r"request rejected", re.IGNORECASE),
        ],
    ),
    (
        "sandbox_readonly",
        [
            re.compile(r"sandbox.*read[- ]?only", re.IGNORECASE),
            re.compile(r"read[- ]?only sandbox", re.IGNORECASE),
        ],
    ),
    (
        "auth_required",
        [
            re.compile(r"permission denied", re.IGNORECASE),
            re.compile(r"authentication required", re.IGNORECASE),
            re.compile(r"not authenticated", re.IGNORECASE),
            re.compile(r"invalid api key", re.IGNORECASE),
            re.compile(r"login required", re.IGNORECASE),
        ],
    ),
    (
        "network_unavailable",
        [
            re.compile(r"network (?:is )?unreachable", re.IGNORECASE),
            re.compile(r"connection (?:refused|reset|timed out)", re.IGNORECASE),
            re.compile(r"failed to connect", re.IGNORECASE),
            re.compile(r"name or service not known", re.IGNORECASE),
        ],
    ),
    (
        "tool_missing",
        [
            re.compile(r"command not found", re.IGNORECASE),
            re.compile(r"no such file or directory.*(?:bin|cli)", re.IGNORECASE),
            re.compile(r"(?:agent|codex|claude|cursor).*not found", re.IGNORECASE),
        ],
    ),
    (
        "timeout",
        [
            re.compile(r"\btimeout\b", re.IGNORECASE),
            re.compile(r"timed out", re.IGNORECASE),
            re.compile(r"deadline exceeded", re.IGNORECASE),
        ],
    ),
]

# Backward-compatible aliases returned by older launchers / logs
LEGACY_ERROR_ALIASES: dict[str, str] = {
    "sandbox_read_only": "sandbox_readonly",
    "permission_denied": "auth_required",
    "cli_error": "tool_missing",
    "request_rejected": "quota_exhausted",
}


def normalize_error_code(code: str | None) -> str | None:
    if not code:
        return None
    if code in NORMALIZED_ERROR_CODES:
        return code
    return LEGACY_ERROR_ALIASES.get(code, code)


def shell_with_pipefail(inner: str) -> str:
    """Wrap a bash -lc fragment so pipeline failures are not masked by tee."""
    return f"set -o pipefail; {inner}"


def detect_log_error_mode(log_text: str) -> str | None:
    for normalized, patterns in ERROR_PATTERN_GROUPS:
        for pattern in patterns:
            if pattern.search(log_text):
                return normalized
    return None


def map_runtime_log_to_normalized(log_text: str, runtime: str | None = None) -> str | None:
    """Map launcher log text to a normalized error code (runtime hint optional)."""
    _ = runtime
    return detect_log_error_mode(log_text)


def evaluate_worker_outcome(
    *,
    pipeline_returncode: int,
    result_md: Path,
    result_json: Path,
    json_extracted: bool,
    log_text: str = "",
    min_md_bytes: int = MIN_RESULT_MD_BYTES,
    require_json_file: bool = False,
    runtime: str | None = None,
) -> tuple[bool, str | None, dict]:
    """Return (ok, error, details) after an external worker CLI run."""
    details: dict = {
        "pipeline_returncode": pipeline_returncode,
        "result_markdown_exists": result_md.exists(),
        "result_json_exists": result_json.exists(),
        "json_extracted": json_extracted,
    }

    if pipeline_returncode != 0:
        details["normalized_error"] = "tool_missing" if pipeline_returncode == 127 else f"cli_exit_{pipeline_returncode}"
        return False, details["normalized_error"], details

    if not log_text and result_md.exists():
        log_text = result_md.read_text(encoding="utf-8", errors="replace")

    log_error = map_runtime_log_to_normalized(log_text, runtime)
    if log_error:
        details["log_error_mode"] = log_error
        details["normalized_error"] = normalize_error_code(log_error)
        return False, log_error, details

    if not result_md.is_file():
        return False, "missing_result_markdown", details

    md_size = result_md.stat().st_size
    details["result_markdown_bytes"] = md_size
    if md_size < min_md_bytes:
        return False, "result_markdown_too_small", details

    if require_json_file:
        if not result_json.is_file():
            return False, "missing_result_json", details
    elif not result_json.is_file() and not json_extracted:
        return False, "missing_result_json", details

    return True, None, details


def run_outcome_fixture_checks() -> list[str]:
    """Self-check fixtures: no external CLI spawn."""
    errors: list[str] = []
    fixtures = Path(__file__).resolve().parent / "fixtures"

    fixture_expectations = {
        "tee_ok_cli_failed.log": "quota_exhausted",
        "claude_429_budget.log": "quota_exhausted",
        "sandbox_readonly.log": "sandbox_readonly",
        "auth_required.log": "auth_required",
        "network_unavailable.log": "network_unavailable",
        "tool_missing.log": "tool_missing",
        "timeout.log": "timeout",
    }

    for name, expected in fixture_expectations.items():
        path = fixtures / name
        if not path.exists():
            errors.append(f"missing fixture: {name}")
            continue
        mode = detect_log_error_mode(path.read_text(encoding="utf-8"))
        normalized = normalize_error_code(mode)
        if normalized != expected:
            errors.append(f"{name}: expected {expected}, got {normalized}")

    tee_ok_log = (fixtures / "tee_ok_cli_failed.log").read_text(encoding="utf-8")
    ok, err, details = evaluate_worker_outcome(
        pipeline_returncode=0,
        result_md=fixtures / "nonexistent.md",
        result_json=fixtures / "nonexistent.json",
        json_extracted=False,
        log_text=tee_ok_log,
        runtime="claude-code",
    )
    if ok or err != "quota_exhausted":
        errors.append(f"tee_ok_cli_failed: expected quota_exhausted, got ok={ok} err={err}")
    if details.get("normalized_error") != "quota_exhausted":
        errors.append("tee_ok_cli_failed missing normalized_error")

    stub_md = fixtures / "_selfcheck_stub.md"
    stub_md.write_text("x" * MIN_RESULT_MD_BYTES, encoding="utf-8")
    try:
        ok, err, _ = evaluate_worker_outcome(
            pipeline_returncode=0,
            result_md=stub_md,
            result_json=fixtures / "missing.json",
            json_extracted=False,
            log_text="worker completed normally\n",
            require_json_file=True,
            runtime="codex",
        )
        if ok or err != "missing_result_json":
            errors.append(f"codex_missing_json: expected missing_result_json, got ok={ok} err={err}")
    finally:
        stub_md.unlink(missing_ok=True)

    return errors


def finding_dedup_key(item: dict) -> tuple:
    """Dedup key for review findings: title + task_id + severity + source."""
    title = item.get("title") or item.get("raw") or json.dumps(item, sort_keys=True)
    return (
        title,
        item.get("task_id") or item.get("reviewer_task_id"),
        item.get("severity", "P2"),
        item.get("source", ""),
    )


def finding_content_hash(item: dict) -> str:
    payload = json.dumps(item, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def dedupe_findings(findings: list[dict], group_duplicates: bool = True) -> list[dict]:
    """Dedupe findings within a sync cycle using key + content hash."""
    if not group_duplicates:
        return list(findings)

    seen_keys: dict[tuple, dict] = {}
    seen_hashes: set[str] = set()
    grouped: list[dict] = []

    for item in findings:
        content_hash = finding_content_hash(item)
        if content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)

        key = finding_dedup_key(item)
        if key in seen_keys:
            seen_keys[key]["count"] = seen_keys[key].get("count", 1) + 1
            continue

        copy = dict(item)
        copy["count"] = 1
        seen_keys[key] = copy
        grouped.append(copy)

    return grouped


def run_dedup_self_check() -> list[str]:
    errors: list[str] = []
    findings = [
        {"title": "Missing error handling", "task_id": "T003", "severity": "P1", "source": "reviewer-a"},
        {"title": "Missing error handling", "task_id": "T004", "severity": "P1", "source": "reviewer-b"},
        {"title": "Missing error handling", "task_id": "T003", "severity": "P2", "source": "reviewer-a"},
    ]
    deduped = dedupe_findings(findings)
    if len(deduped) != 3:
        errors.append(f"expected 3 distinct findings after dedup, got {len(deduped)}")

    exact_dup = findings + [dict(findings[0])]
    deduped_exact = dedupe_findings(exact_dup)
    if len(deduped_exact) != 3:
        errors.append(f"hash dedup failed: expected 3, got {len(deduped_exact)}")

    return errors
