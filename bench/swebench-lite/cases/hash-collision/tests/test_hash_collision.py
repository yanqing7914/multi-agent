import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1] / "repo"
sys.path.insert(0, str(REPO))

from hash.table import HashTable  # noqa: E402


def test_collision_chain_retrieves_both_values():
    # size=1 forces all keys into the same bucket regardless of hash salt
    table = HashTable(size=1)
    table.set("beta", "B")
    table.set("delta", "D")
    assert table.get("beta") == "B"
    assert table.get("delta") == "D"


def test_update_existing_key():
    table = HashTable(size=4)
    table.set("user", "v1")
    table.set("user", "v2")
    assert table.get("user") == "v2"


def test_stable_indexing():
    table = HashTable(size=8)
    table.set("ping", "pong")
    assert table.get("ping") == "pong"
