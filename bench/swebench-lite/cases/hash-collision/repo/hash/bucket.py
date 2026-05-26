"""Chaining bucket for hash collisions."""


class Bucket:
    def __init__(self) -> None:
        self._entries: list[tuple[str, str]] = []

    def put(self, key: str, value: str) -> None:
        for index, (existing_key, _) in enumerate(self._entries):
            if existing_key == key:
                self._entries[index] = (key, value)
                return
        self._entries.append((key, value))

    def get(self, key: str) -> str | None:
        # BUG: only inspects the first entry in the bucket
        if self._entries and self._entries[0][0] == key:
            return self._entries[0][1]
        return None

    def keys(self) -> list[str]:
        return [key for key, _ in self._entries]
