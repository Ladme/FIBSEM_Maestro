# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from fibsem_maestro.microscope.abstract_control.microscope_control import (
    MicroscopeControl,
)
from fibsem_maestro.microscope.microscope_registry import MicroscopeRegistry


@MicroscopeRegistry.register("simulated")
class SimulatedMicroscopeControl(MicroscopeControl):
    pass
