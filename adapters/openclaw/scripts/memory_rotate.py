#!/usr/bin/env python3
"""Rotate and compact MEMORY.md when it grows too large (dependency-free)."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent


def utc_datestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def split_memory_sections(lines: list[str]) -> tuple[list[str], list[str]]:
    """Return (header_lines, body_lines). Header = initial # title + intro until first blank after header block."""
    if not lines:
        return ["# Project Memory\n", "\n"], []
    header: list[str] = []
    body_start = 0
    if lines[0].startswith("#"):
        header.append(lines[0])
        body_start = 1
        while body_start < len(lines) and (lines[body_start].strip() or body_start < 3):
            header.append(lines[body_start])
            body_start += 1
    body = lines[body_start:]
    return header, body


def rotate_memory(path: Path, max_lines: int = 200, keep_recent: int = 80) -> dict:
    if not path.exists():
        return {"ok": True, "rotated": False, "reason": "memory file missing", "path": str(path)}

    raw_lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    total = len(raw_lines)
    if total <= max_lines:
        return {"ok": True, "rotated": False, "lines": total, "max_lines": max_lines, "path": str(path)}

    header, body = split_memory_sections(raw_lines)
    archive_name = path.parent / f"MEMORY.archive.{utc_datestamp()}.md"
    archive_name.write_text("".join(raw_lines), encoding="utf-8")

    keep_recent = min(keep_recent, max(1, max_lines - len(header)))
    compact_body = body[-keep_recent:] if keep_recent else []
    compact = header + compact_body
    path.write_text("".join(compact), encoding="utf-8")

    return {
        "ok": True,
        "rotated": True,
        "path": str(path),
        "archive": str(archive_name),
        "lines_before": total,
        "lines_after": len(compact),
        "max_lines": max_lines,
        "keep_recent": keep_recent,
    }


def run_self_check() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="memory-rotate-") as tmp:
        workspace = Path(tmp)
        memory = workspace / "MEMORY.md"
        lines = ["# Project Memory\n", "\n", "Append-only log.\n", "\n"]
        lines.extend(f"- line {i}\n" for i in range(250))
        memory.write_text("".join(lines), encoding="utf-8")

        result = rotate_memory(memory, max_lines=200, keep_recent=60)
        if not result.get("ok"):
            errors.append("rotate_memory returned not ok")
        if not result.get("rotated"):
            errors.append("expected rotation for 250 lines")
        archive = Path(result.get("archive", ""))
        if not archive.exists():
            errors.append("archive file missing")
        after = memory.read_text(encoding="utf-8").splitlines()
        if len(after) > 200:
            errors.append(f"compact file still too large: {len(after)}")

        small = workspace / "MEMORY.small.md"
        small.write_text("# Project Memory\n\n- one line\n", encoding="utf-8")
        noop = rotate_memory(small, max_lines=200)
        if noop.get("rotated"):
            errors.append("small file should not rotate")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "memory_rotate self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-path", default=str(REPO_ROOT / "MEMORY.md"), help="Path to MEMORY.md")
    parser.add_argument("--max-lines", type=int, default=200, help="Rotate when file exceeds this many lines")
    parser.add_argument("--keep-recent", type=int, default=80, help="Body lines to retain after rotation")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    path = Path(args.memory_path).expanduser().resolve()
    result = rotate_memory(path, max_lines=args.max_lines, keep_recent=args.keep_recent)
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
