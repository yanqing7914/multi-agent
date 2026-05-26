import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP.parent))

from app.routes import health_payload, index_payload, ping_payload, version_payload  # noqa: E402


def test_health_payload():
    data = health_payload()
    assert data["status"] == "ok"


def test_index_payload_mentions_service():
    data = index_payload()
    assert "hello" in data["message"]


def test_version_payload():
    data = version_payload()
    assert data == {"version": "0.1.0"}


def test_ping_payload():
    data = ping_payload()
    assert data == {"pong": True}
