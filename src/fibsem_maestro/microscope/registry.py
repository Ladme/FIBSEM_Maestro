# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from fibsem_maestro.core.registry import Registry
from fibsem_maestro.microscope.abstract_control.microscope_control import (
    MicroscopeControl,
)

MICROSCOPE_CONTROLS = Registry[type[MicroscopeControl]]("microscope control")
