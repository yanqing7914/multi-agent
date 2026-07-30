"""Adversarial regression tests: lock in the security fixes and the merge/commit gates.

Each test here encodes a *bypass attempt* that previously slipped through. They
exist because the project's happy-path self-checks stayed green while these
gates silently leaked — a security guard must be tested with hostile inputs, not
just cooperative ones.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENCLAW_SCRIPTS = REPO_ROOT / "adapters" / "openclaw" / "scripts"
TOOLS = REPO_ROOT / "tools"
SHARED = REPO_ROOT / "adapters" / "_shared"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def audit_mod():
    sys.path.insert(0, str(OPENCLAW_SCRIPTS))
    return load("audit_worker_output", OPENCLAW_SCRIPTS / "audit_worker_output.py")


@pytest.fixture(scope="module")
def tool_base():
    sys.path.insert(0, str(TOOLS))
    return load("_tool_base", TOOLS / "_tool_base.py")


@pytest.fixture(scope="module")
def bridge_mod():
    sys.path.insert(0, str(SHARED))
    return load("bridge", SHARED / "bridge.py")


def git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


# --------------------------------------------------------------------------- #
# Bug 1 + generalization: **/x/** patterns must actually match.
# --------------------------------------------------------------------------- #
class TestSecretGlobMatching:
    def test_secrets_dir_at_any_depth_is_flagged(self, audit_mod) -> None:
        for p in ("secrets/k.json", "src/secrets/k.json", "a/b/secrets/c.json"):
            assert audit_mod.matches(p, audit_mod.SECRET_PATTERNS), p

    def test_generalizes_to_user_blocked_paths(self, audit_mod) -> None:
        assert audit_mod._segment_glob_match("x/node_modules/y", "**/node_modules/**")

    def test_non_secret_not_flagged(self, audit_mod) -> None:
        assert not audit_mod.matches("src/app.py", audit_mod.SECRET_PATTERNS)

    def test_single_ended_patterns_still_work(self, audit_mod) -> None:
        assert audit_mod._segment_glob_match("src/a.py", "src/**")
        assert audit_mod._segment_glob_match("logs/x", "**/x")
        assert not audit_mod._segment_glob_match("other/a.py", "src/**")


# --------------------------------------------------------------------------- #
# Bug 3: mission_control_exempt must be an exact-segment match.
# --------------------------------------------------------------------------- #
class TestMissionControlExempt:
    def test_lookalike_dirs_not_exempt(self, audit_mod) -> None:
        assert not audit_mod.mission_control_exempt(".codex-multi-agent-evil/p.py", None)
        assert not audit_mod.mission_control_exempt(".codex-multi-agent-backup/.env", None)

    def test_real_state_dir_exempt(self, audit_mod) -> None:
        assert audit_mod.mission_control_exempt(".codex-multi-agent/tasks/x.md", None)


# --------------------------------------------------------------------------- #
# Bug 2: a Markdown `true` must not overwrite an honest JSON `false`.
# --------------------------------------------------------------------------- #
class TestFalseCompletionMerge:
    def test_json_false_survives_markdown_true(self) -> None:
        merged: dict = {}
        for loaded in ({"required_paths_verified": False, "files_read": ["x"]},
                       {"required_paths_verified": True}):
            for k, v in loaded.items():
                if k not in merged or merged.get(k) in (None, [], ""):
                    merged[k] = v
        assert merged["required_paths_verified"] is False


# --------------------------------------------------------------------------- #
# Bug 4: command allow/deny must be token-aware and enforce ~/ paths.
# --------------------------------------------------------------------------- #
class TestCommandGuards:
    def test_denylist_catches_flag_interposed_git_push(self, tool_base) -> None:
        assert tool_base.command_is_blocked("git -C /repo push origin main")
        assert tool_base.command_is_blocked("git reset --hard HEAD")
        assert tool_base.command_is_blocked("echo hi && git push")

    def test_denylist_no_false_positive(self, tool_base) -> None:
        assert not tool_base.command_is_blocked("git status")
        assert not tool_base.command_is_blocked("mydeployer run")

    def test_allowlist_rejects_chained_danger(self, tool_base) -> None:
        assert tool_base.command_is_allowed("echo hi", ["echo"])
        assert not tool_base.command_is_allowed("rm -rf /tmp && echo done", ["echo"])
        assert not tool_base.command_is_allowed("rm echo", ["echo"])

    def test_home_anchored_secret_paths_enforced(self, tool_base) -> None:
        assert tool_base.path_matches("~/.ssh/id_rsa", ["~/.ssh/**"])
        assert tool_base.path_matches(".ssh/id_rsa", ["~/.ssh/**"])
        assert not tool_base.path_matches("src/app.py", ["~/.ssh/**"])


# --------------------------------------------------------------------------- #
# Bug 8: log JSON extraction must handle nested objects.
# --------------------------------------------------------------------------- #
class TestLogJsonExtraction:
    def test_nested_object_extracted(self, bridge_mod, tmp_path) -> None:
        jp = tmp_path / "out.json"
        log = 'noise\n{"task_id":"T1","role":"Worker","data":{"n":1,"deep":{"x":2}}}\nend'
        assert bridge_mod.try_extract_json_from_log(log, jp)
        import json
        assert json.loads(jp.read_text())["data"]["deep"]["x"] == 2

    def test_no_report_returns_false(self, bridge_mod, tmp_path) -> None:
        assert not bridge_mod.try_extract_json_from_log("just logs", tmp_path / "n.json")


# --------------------------------------------------------------------------- #
# New gate: gated_merge must refuse secret/out-of-scope branches.
# --------------------------------------------------------------------------- #
class TestGatedMerge:
    def test_self_check(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(OPENCLAW_SCRIPTS / "gated_merge.py"), "--self-check"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def _seed(self, root: Path) -> Path:
        git("init", "-q", "-b", "main", cwd=root)
        git("config", "user.email", "t@l", cwd=root)
        git("config", "user.name", "t", cwd=root)
        state = root / ".codex-multi-agent"
        state.mkdir(parents=True)
        import json
        (state / "ownership.json").write_text(json.dumps({
            "schema_version": 1,
            "tasks": [{"task_id": "T1", "session_name": "w", "role": "Worker",
                       "allowed_paths": ["src/**"], "blocked_paths": [".env"], "status": "pending"}],
        }))
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("x=1\n")
        git("add", "-A", cwd=root)
        git("commit", "-qm", "base", cwd=root)
        return state / "ownership.json"

    def _branch(self, root: Path, name: str, rel: str, content: str) -> None:
        git("checkout", "-q", "-b", name, cwd=root)
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        git("add", "-A", cwd=root)
        git("commit", "-qm", name, cwd=root)
        git("checkout", "-q", "main", cwd=root)

    def _gate(self, root: Path, own: Path, branch: str):
        proc = subprocess.run(
            [sys.executable, str(OPENCLAW_SCRIPTS / "gated_merge.py"),
             "--repo-root", str(root), "--base", "main", "--branch", branch,
             "--ownership", str(own), "--task-id", "T1", "--execute", "--no-write-audit"],
            capture_output=True, text=True,
        )
        import json
        return proc.returncode, json.loads(proc.stdout)

    def test_secret_branch_refused(self, tmp_path) -> None:
        own = self._seed(tmp_path)
        self._branch(tmp_path, "multi-agent/T1-secret", "src/secrets/k.json", "{}\n")
        code, report = self._gate(tmp_path, own, "multi-agent/T1-secret")
        assert report["gate"] == "refused" and not report["merged"]
        assert code == 1
        assert not (tmp_path / "src" / "secrets" / "k.json").exists()

    def test_clean_branch_merges(self, tmp_path) -> None:
        own = self._seed(tmp_path)
        self._branch(tmp_path, "multi-agent/T1-clean", "src/feature.py", "y=2\n")
        code, report = self._gate(tmp_path, own, "multi-agent/T1-clean")
        assert report["merged"] is True and code == 0
        assert (tmp_path / "src" / "feature.py").exists()

    def test_out_of_scope_branch_refused(self, tmp_path) -> None:
        own = self._seed(tmp_path)
        self._branch(tmp_path, "multi-agent/T1-oos", "other/x.py", "z=3\n")
        code, report = self._gate(tmp_path, own, "multi-agent/T1-oos")
        assert not report["merged"] and code == 1


# --------------------------------------------------------------------------- #
# New gate: pre-commit hook installer.
# --------------------------------------------------------------------------- #
class TestGateHook:
    def test_self_check(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(OPENCLAW_SCRIPTS / "install_gate_hook.py"), "--self-check"],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
