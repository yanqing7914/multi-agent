"""Argparse entrypoint."""

import argparse

from .config import DEFAULT_HOST, DEFAULT_PORT
from .server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Flask-shaped CLI demo (stdlib http.server)")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Start HTTP server")
    run_cmd.add_argument("--host", default=DEFAULT_HOST)
    run_cmd.add_argument("--port", type=int, default=DEFAULT_PORT)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        run_server(host=args.host, port=args.port)
        return 0
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
