# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


class LogLine:
    """Parsed log line."""

    __slots__ = ("timestamp", "name", "level", "message", "raw")

    def __init__(
        self, timestamp: str, name: str, level: str, message: str, raw: str
    ) -> None:
        self.timestamp = timestamp
        self.name = name
        self.level = level
        self.message = message
        self.raw = raw
