# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Parsing of the lines of the per-slice `run.log` files."""

import logging
import re

# log line pattern: "2026-06-23 14:39:25,801 [name] LEVEL: message"
LOG_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[([^\]]+)\] (\w+): (.*)$"
)

LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]

LEVEL_COLORS = {
    "DEBUG": "#888888",
    "INFO": "#cccccc",
    "WARNING": "#f0c040",
    "ERROR": "#f44336",
}


class LogLine:
    """
    Parsed log line.

    Args:
        timestamp: "YYYY-MM-DD HH:MM:SS,mmm"; sorts chronologically as text.
        name: The logger name.
        level: The level name, e.g. "INFO".
        message: The message.
        raw: The whole line, without the line break.
    """

    __slots__ = ("timestamp", "name", "level", "message", "raw")

    def __init__(
        self, timestamp: str, name: str, level: str, message: str, raw: str
    ) -> None:
        self.timestamp = timestamp
        self.name = name
        self.level = level
        self.message = message
        self.raw = raw


def level_value(level: str) -> int:
    """
    The numeric value of a level name.

    Args:
        level: E.g. "INFO".

    Returns:
        The `logging` value; DEBUG's for an unknown name.
    """
    return getattr(logging, level, logging.DEBUG)


def parse_line(line: str) -> LogLine | None:
    """
    Parse one line of a log file.

    Args:
        line: The line, with or without the line break.

    Returns:
        The parsed line, or None if it does not start a log record (e.g. a
        traceback line).
    """
    m = LOG_RE.match(line.rstrip())
    if not m:
        return None
    return LogLine(
        timestamp=m.group(1),
        name=m.group(2),
        level=m.group(3),
        message=m.group(4),
        raw=line.rstrip(),
    )
