# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from __future__ import annotations

from collections.abc import Callable
from typing import TypeAlias

from fibsem_maestro.core.registry import Registry
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.microscope_control import (
    MicroscopeControl,
)

MicroscopeControlFactory: TypeAlias = Callable[
    [str, int | None, TextLogger], MicroscopeControl
]
"""Connects to a microscope: `(ip_address, port, txt_log) -> control`. Control classes qualify."""

MICROSCOPE_CONTROLS = Registry[MicroscopeControlFactory]("microscope control")
