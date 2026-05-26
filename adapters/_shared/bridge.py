#!/usr/bin/env python3
"""Shared bridge helpers for thin client adapters (dependency-free)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OPENCLAW_SCRIPTS = REPO_ROOT / "adapters" / "openclaw" / "scripts"
OPENCLAW_TEMPLATES = REPO_ROOT / "adapters" / "openclaw" / "templates"
MCP_SELF_CHECK = REPO_ROOT / "mcp" / "multi-agent-coordinator" / "scripts" / "self_check.py"
PANEL_SELF_CHECK = REPO_ROOT / "ide" / "multi-agent-panel" / "scripts" / "self_check.py"
RESULT_REPORT_TEMPLATE = OPENCLAW_TEMPLATES / "result-report.md"
TASK_CARD_TEMPLATE = OPENCLAW_TEMPLATES / "task-card.md"
CREATE_TASK_CARDS = OPENCLAW_SCRIPTS / "create_task_cards.py"
VERIFY_WORKSPACE = OPENCLAW_SCRIPTS / "verify_workspace.py"


def _parse_list_block(text: str, key: str) -> list[str]:
    pattern = rf"^{re.escape(key)}:\s*\n((?:  - .+\n)*)"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        single = re.search(rf"^{re.escape(key)}:\s*\[\]\s*$", text, re.MULTILINE)
        return [] if single else []
    block = match.group(1)
    return [line.strip()[2:].strip() for line in block.splitlines() if line.strip().startswith("- ")]


def _parse_scalar(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _parse_nested_scalars(text: str, key: str) -> dict[str, str]:
    pattern = rf"^{re.escape(key)}:\s*\n((?:  \w+: .+\n)*)"
    match = re.search(pattern, text, re.MULTILINE)
    if not match:
        return {}
    result: dict[str, str] = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if ":" in stripped:
            sub_key, sub_val = stripped.split(":", 1)
            result[sub_key.strip()] = sub_val.strip()
    return result


def parse_task_card(path: Path) -> dict:
    """Parse the YAML-like task card markdown emitted by create_task_cards.py."""
    text = path.read_text(encoding="utf-8")
    result_report_paths = _parse_nested_scalars(text, "result_report_paths")
    data: dict = {
        "task_id": _parse_scalar(text, "task_id"),
        "session_name": _parse_scalar(text, "session_name"),
        "runtime": _parse_scalar(text, "runtime"),
        "mode": _parse_scalar(text, "mode"),
        "role": _parse_scalar(text, "role"),
        "title": _parse_scalar(text, "title"),
        "objective": _parse_scalar(text, "objective"),
        "workspace_root": _parse_scalar(text, "workspace_root"),
        "target_repo": _parse_scalar(text, "target_repo"),
        "write_permission": _parse_scalar(text, "write_permission"),
        "preflight_command": _parse_list_block(text, "preflight_command"),
        "tools_used": _parse_list_block(text, "tools_used"),
        "required_paths": _parse_list_block(text, "required_paths"),
        "allowed_paths": _parse_list_block(text, "allowed_paths"),
        "dependencies": _parse_list_block(text, "dependencies"),
        "execution_guidance": _parse_list_block(text, "execution_guidance"),
        "result_report_paths": result_report_paths,
        "result_json_path": result_report_paths.get("json", ""),
        "result_markdown_path": result_report_paths.get("markdown", ""),
    }
    return data


def workspace_root_from_card(card: dict, state_dir: Path | None = None) -> Path:
    root = card.get("workspace_root") or card.get("target_repo")
    if root:
        return Path(str(root)).expanduser().resolve()
    if state_dir is not None:
        ownership = state_dir / "ownership.json"
        if ownership.exists():
            payload = json.loads(ownership.read_text(encoding="utf-8"))
            if payload.get("workspace_root"):
                return Path(payload["workspace_root"]).expanduser().resolve()
    raise ValueError("task card missing workspace_root / target_repo")


def run_preflight(workspace_root: Path, required_paths: list[str]) -> tuple[int, dict]:
    cmd = [
        sys.executable,
        str(VERIFY_WORKSPACE),
        "--workspace-root",
        str(workspace_root),
        "--json",
    ]
    if required_paths:
        cmd.extend(["--required-paths", *required_paths])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    payload: dict = {"returncode": proc.returncode}
    if proc.stdout.strip():
        try:
            payload.update(json.loads(proc.stdout))
        except json.JSONDecodeError:
            payload["stdout"] = proc.stdout.strip()
    if proc.stderr.strip():
        payload["stderr"] = proc.stderr.strip()
    return proc.returncode, payload


def build_worker_prompt(task_card_path: Path, card: dict, workspace_root: Path) -> str:
    """Compose the worker prompt with mandatory preflight and result-report contract."""
    preflight_lines = card.get("preflight_command") or []
    json_path = card.get("result_json_path") or ""
    md_path = card.get("result_markdown_path") or ""
    task_body = task_card_path.read_text(encoding="utf-8").strip()
    preflight_block = "\n".join(f"  {line}" for line in preflight_lines)
    return (
        "You are a scoped multi-agent worker. Follow the task card exactly.\n\n"
        "MANDATORY FIRST STEPS (do not skip):\n"
        f"  cd {workspace_root}\n"
        f"  pwd\n"
        f"{preflight_block}\n\n"
        "If preflight fails or required paths are missing:\n"
        "  - set status=blocked, required_paths_verified=false\n"
        "  - list missing paths in required_paths_missing\n"
        "  - do not claim completed work on unread files\n\n"
        "Before finishing, write BOTH result reports listed in result_report_paths:\n"
        f"  JSON: {json_path}\n"
        f"  Markdown: {md_path}\n"
        "Use the schema in adapters/openclaw/templates/result-report.md.\n"
        "Set workspace_observed to pwd after cd. List every file opened in files_read.\n"
        "List every framework tool invoked in tools_used (mirrors files_read).\n\n"
        "--- TASK CARD ---\n"
        f"{task_body}\n"
        "--- END TASK CARD ---\n"
    )


def tee_run(cmd: list[str], log_path: Path, cwd: Path | None = None) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log_file:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=str(cwd) if cwd else None,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            sys.stdout.write(line)
            log_file.write(line)
        return proc.wait()


def try_extract_json_from_log(log_text: str, json_path: Path) -> bool:
    """Best-effort: extract a JSON object from worker log into result sidecar."""
    if json_path.exists():
        return True
    matches = re.findall(r"\{[\s\S]*?\}", log_text)
    for candidate in reversed(matches):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("task_id") and payload.get("role"):
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return True
    return False
