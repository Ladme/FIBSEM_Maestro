# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


# importing the modules registers the controls; the Autoscript control is
# registered by a factory that imports Autoscript only when connecting
from . import autoscript_factory as autoscript_factory
from .mock.microscope_control import MockMicroscopeControl as MockMicroscopeControl
from .simulated.microscope_control import (
    SimulatedMicroscopeControl as SimulatedMicroscopeControl,
)
