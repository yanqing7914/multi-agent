#!/usr/bin/env python3
"""One-command launcher for the mission-control IDE panel.

Wraps `ide/multi-agent-panel/server.py` with sane defaults, an automatic free
port, and an optional browser open, so a user can go from a `.codex-multi-agent/`
state directory to a live task board in one command:

  python ide/multi-agent-panel/scripts/open_panel.py --state-dir .codex-multi-agent

Dependency-free (stdlib only). `--self-check` validates wiring without serving.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import webbrowser
from pathlib import Path

PANEL_DIR = Path(__file__).resolve().parent.parent
SERVER = PANEL_DIR / "server.py"
if str(PANEL_DIR) not in sys.path:
    sys.path.insert(0, str(PANEL_DIR))


def _port_is_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def find_free_port(host: str, preferred: int, attempts: int = 20) -> int:
    for offset in range(attempts):
        candidate = preferred + offset
        if _port_is_free(host, candidate):
            return candidate
    # Fall back to an ephemeral port chosen by the OS.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def serve(state_dir: Path, host: str, port: int, write: bool, refresh: int, open_browser: bool) -> int:
    import server as panel  # noqa: E402  (imported lazily; sibling module)
    from http.server import ThreadingHTTPServer

    state_dir.mkdir(parents=True, exist_ok=True)
    panel.PanelHandler.state_dir = state_dir
    panel.PanelHandler.write_enabled = write
    panel.PanelHandler.refresh_seconds = refresh

    httpd = ThreadingHTTPServer((host, port), panel.PanelHandler)
    url = f"http://{host}:{port}/"
    print(
        json.dumps(
            {"ok": True, "url": url, "state_dir": str(state_dir), "write_enabled": write},
            indent=2,
        ),
        flush=True,
    )
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


def run_self_check() -> int:
    """Validate launcher wiring without binding a long-lived server."""
    import tempfile

    errors: list[str] = []
    if not SERVER.is_file():
        errors.append(f"panel server.py not found at {SERVER}")
    static_index = PANEL_DIR / "static" / "index.html"
    if not static_index.is_file():
        errors.append("panel static/index.html missing")

    try:
        import server as panel  # noqa: F401

        if not hasattr(panel, "PanelHandler") or not hasattr(panel, "load_state_bundle"):
            errors.append("server module missing PanelHandler/load_state_bundle")
        else:
            with tempfile.TemporaryDirectory(prefix="open-panel-selfcheck-") as tmp:
                bundle = panel.load_state_bundle(Path(tmp))
                if not isinstance(bundle, dict) or not bundle.get("ok"):
                    errors.append("load_state_bundle did not return ok bundle for empty state")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"failed to import panel server: {exc}")

    # Free-port finder must return a bindable port.
    try:
        port = find_free_port("127.0.0.1", 9876)
        if not _port_is_free("127.0.0.1", port):
            errors.append("find_free_port returned a busy port")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"find_free_port failed: {exc}")

    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "message": "open_panel self-check passed"}, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--state-dir", default=".codex-multi-agent", help="Mission-control state directory")
    parser.add_argument("--port", type=int, default=9876, help="Preferred port (auto-advances if busy)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--write", action="store_true", help="Enable POST sync/audit/summarize endpoints")
    parser.add_argument("--refresh", type=int, default=5, help="UI poll interval seconds")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser window")
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()

    if args.self_check:
        return run_self_check()

    state_dir = Path(args.state_dir).expanduser().resolve()
    port = args.port if _port_is_free(args.host, args.port) else find_free_port(args.host, args.port)
    return serve(state_dir, args.host, port, args.write, args.refresh, not args.no_browser)


if __name__ == "__main__":
    raise SystemExit(main())
