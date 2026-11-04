# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
Registers the Autoscript microscope control without importing Autoscript.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fibsem_maestro.core.errors import AutoscriptNotAvailableError
from fibsem_maestro.microscope.registry import MICROSCOPE_CONTROLS

if TYPE_CHECKING:
    from fibsem_maestro.logging.text.text_logger import TextLogger
    from fibsem_maestro.microscope.abstract_control.microscope_control import (
        MicroscopeControl,
    )

_AUTOSCRIPT_PACKAGES = ("autoscript", "thermoscientific")
"""Top-level package prefixes of the Autoscript distribution."""


@MICROSCOPE_CONTROLS.register("autoscript")
def connect_autoscript(
    ip_address: str, port: int | None, txt_log: TextLogger
) -> MicroscopeControl:
    """
    Connect to a microscope through Autoscript.

    Args:
        ip_address: Network address of the microscope server.
        port: Port of the microscope server, or `None` for the default.
        txt_log: Logger for diagnostic and status messages.

    Returns:
        The connected Autoscript microscope control.

    Raises:
        AutoscriptNotAvailableError: If Autoscript is not linked.
    """
    try:
        from fibsem_maestro.microscope.autoscript_control.microscope_control import (
            AutoscriptMicroscopeControl,
        )
    except ModuleNotFoundError as e:
        if e.name is None or not e.name.startswith(_AUTOSCRIPT_PACKAGES):
            raise
        raise AutoscriptNotAvailableError() from e

    return AutoscriptMicroscopeControl(ip_address, port, txt_log)
