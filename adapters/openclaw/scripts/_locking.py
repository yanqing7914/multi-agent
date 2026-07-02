"""Cross-platform advisory file lock for mission-control state directories.

Parallel Workers are a first-class scenario: several `update_task_status.py`
processes may update `ownership.json` / `status.json` at the same time. Every
writer performs read-modify-write on whole JSON documents, so without mutual
exclusion the last writer silently discards earlier updates (and concurrent
writes can tear the files). All state mutations must run inside `state_lock`.
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

if os.name == "nt":
    import msvcrt
else:
    import fcntl

LOCK_FILENAME = ".state.lock"
DEFAULT_TIMEOUT_S = 30.0


class StateLockTimeout(TimeoutError):
    """Raised when the state lock cannot be acquired within the timeout."""


def _try_acquire(handle) -> bool:
    try:
        if os.name == "nt":
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _release(handle) -> None:
    try:
        if os.name == "nt":
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass


@contextmanager
def state_lock(
    state_dir: Path,
    timeout: float = DEFAULT_TIMEOUT_S,
    poll_interval: float = 0.05,
) -> Iterator[None]:
    """Exclusive advisory lock scoped to one mission-control state directory."""
    state_dir = Path(state_dir)
    state_dir.mkdir(parents=True, exist_ok=True)
    lock_path = state_dir / LOCK_FILENAME
    handle = open(lock_path, "a+b")
    deadline = time.monotonic() + timeout
    try:
        while not _try_acquire(handle):
            if time.monotonic() >= deadline:
                raise StateLockTimeout(
                    f"could not acquire state lock {lock_path} within {timeout}s "
                    "(another mission-control process is holding it)"
                )
            time.sleep(poll_interval)
        yield
    finally:
        _release(handle)
        handle.close()


def atomic_write_text(path: Path, text: str) -> None:
    """Write via temp file + os.replace so concurrent readers never see torn JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)
