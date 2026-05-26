"""Route handlers for the demo HTTP server."""

from .config import DEFAULT_HOST, DEFAULT_PORT


def health_payload() -> dict:
    return {"status": "ok", "service": "flask-cli-demo"}


def index_payload() -> dict:
    return {
        "message": "hello from flask-cli demo",
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
    }


def version_payload() -> dict:
    return {"version": "0.1.0"}


def ping_payload() -> dict:
    return {"pong": True}


def echo_payload(msg: str) -> dict:
    return {"echo": msg}
