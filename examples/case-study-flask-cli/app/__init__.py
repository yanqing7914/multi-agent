"""Tiny CLI + HTTP server (stdlib only, Flask-shaped layout)."""

from .cli import main
from .server import run_server

__all__ = ["main", "run_server"]
