# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import pytest

from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


@pytest.fixture
def simulated_microscope() -> Microscope:
    return Microscope(
        MicroscopeSettings(control="simulated", ip_address="localhost"),
        MemoryTextLogger(lambda: 0),
    )
