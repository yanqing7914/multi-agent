"""Fixed-size hash table with chaining."""

from .bucket import Bucket
from .constants import INITIAL_BUCKETS, stable_hash


class HashTable:
    def __init__(self, size: int = INITIAL_BUCKETS) -> None:
        self.size = size
        self.buckets = [Bucket() for _ in range(size)]

    def _index(self, key: str) -> int:
        # BUG: uses built-in hash() which is salted per process
        return hash(key) % self.size

    def set(self, key: str, value: str) -> None:
        idx = self._index(key)
        self.buckets[idx].put(key, value)

    def get(self, key: str) -> str | None:
        idx = self._index(key)
        return self.buckets[idx].get(key)
