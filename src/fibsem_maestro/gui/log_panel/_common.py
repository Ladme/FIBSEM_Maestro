# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

import logging
import re

from PyQt6.QtWidgets import QLabel

from fibsem_maestro.gui.log_panel._log_line import LogLine

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


def level_value(level: str) -> int:
    return getattr(logging, level, logging.DEBUG)


def parse_line(line: str) -> LogLine | None:
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


def bold_label(text: str) -> QLabel:
    label = QLabel(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label
