"""
An in-memory stand-in for the parts of the Autoscript client that Maestro uses.
"""

from typing import Any

from autoscript_sdb_microscope_client.enumerations import ScanningMode
from autoscript_sdb_microscope_client.structures import (
    Limits,
    Point,
    Rectangle,
    StagePosition,
)


class _Value:
    """A settable `.value` with `.limits`, like most Autoscript properties."""

    def __init__(self, value: Any, limits: Any = None) -> None:
        self._value = value
        self.limits = limits

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, value: Any) -> None:
        self._value = value


class _WorkingDistance(_Value):
    def set_value_no_degauss(self, value: float) -> None:
        self.value = value


class _Resolution:
    available_values = [
        "512x442",
        "768x512",
        "1024x884",
        "1536x1024",
        "2048x1768",
        "3072x2048",
        "4096x3536",
        "6144x4096",
    ]

    def __init__(self, value: str) -> None:
        self._value = value

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, value: str) -> None:
        self._value = value

    @property
    def width(self) -> int:
        return int(self._value.split("x")[0])

    @property
    def height(self) -> int:
        return int(self._value.split("x")[1])


class _Mode:
    def __init__(self) -> None:
        self._mode = ScanningMode.FULL_FRAME
        self.reduced_area = _Value(Rectangle(0.0, 0.0, 1.0, 1.0))

    @property
    def value(self) -> int:
        return self._mode

    def set_full_frame(self) -> None:
        self._mode = ScanningMode.FULL_FRAME

    def set_reduced_area(
        self, left: float, top: float, width: float, height: float
    ) -> None:
        self._mode = ScanningMode.REDUCED_AREA
        self.reduced_area.value = Rectangle(left, top, width, height)


class _Scanning:
    def __init__(self) -> None:
        self.resolution = _Resolution("1536x1024")
        self.dwell_time = _Value(1e-6)
        self.rotation = _Value(0.0)
        self.mode = _Mode()
        self._bit_depth = 8
        self._line_integration = 1
        self.line_integration_error: Exception | None = None

    @property
    def bit_depth(self) -> int:
        return self._bit_depth

    @bit_depth.setter
    def bit_depth(self, value: int) -> None:
        self._bit_depth = value

    @property
    def line_integration(self) -> int:
        if self.line_integration_error is not None:
            raise self.line_integration_error
        return self._line_integration

    @line_integration.setter
    def line_integration(self, value: int) -> None:
        if self.line_integration_error is not None:
            raise self.line_integration_error
        self._line_integration = value


class _Beam:
    def __init__(self, working_distance_m: float) -> None:
        self.working_distance = _WorkingDistance(
            working_distance_m, Limits(min=1e-3, max=60e-3)
        )
        self.horizontal_field_width = _Value(10e-6, Limits(min=1e-7, max=2e-3))
        self.beam_shift = _Value(Point(0.0, 0.0))
        self.stigmator = _Value(Point(0.0, 0.0))
        self.lens_alignment = _Value(Point(0.0, 0.0))
        self.source_tilt = _Value(Point(0.0, 0.0))
        self.beam_current = _Value(1e-10)
        self.scanning = _Scanning()


class _Stage:
    def __init__(self, default_coordinate_system: str) -> None:
        self.default_coordinate_system = default_coordinate_system
        self.unlink_calls = 0
        self.moves: list[StagePosition] = []
        self._xy = (1e-3, 2e-3)

    def link(self) -> None:
        pass

    def unlink(self) -> None:
        self.unlink_calls += 1

    def set_default_coordinate_system(self, coordinate_system: str) -> None:
        self.default_coordinate_system = coordinate_system

    @property
    def current_position(self) -> StagePosition:
        return StagePosition(
            x=self._xy[0],
            y=self._xy[1],
            z=4e-3,
            r=0.0,
            t=0.0,
            coordinate_system=self.default_coordinate_system,
        )

    def absolute_move(self, position: StagePosition, settings: Any = None) -> None:
        _ = settings
        self.moves.append(position)
        self._xy = (position.x or self._xy[0], position.y or self._xy[1])

    def relative_move(self, delta: StagePosition, settings: Any = None) -> None:
        _ = settings
        self.moves.append(delta)
        self._xy = (self._xy[0] + (delta.x or 0.0), self._xy[1] + (delta.y or 0.0))


class _Specimen:
    def __init__(self, default_coordinate_system: str) -> None:
        self.stage = _Stage(default_coordinate_system)


class _Beams:
    def __init__(self) -> None:
        self.electron_beam = _Beam(working_distance_m=4e-3)
        self.ion_beam = _Beam(working_distance_m=16.5e-3)


class _Imaging:
    def set_active_view(self, index: int) -> None:
        self.active_view = index

    def set_active_device(self, device: int) -> None:
        self.active_device = device


class _AutoFunctions:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def run_auto_focus(self, settings: Any = None) -> None:
        self.calls.append(("auto_focus", settings))

    def run_auto_stigmator(self, settings: Any = None) -> None:
        self.calls.append(("auto_stigmator", settings))


class _Detector:
    def __init__(self) -> None:
        self.type = _Value("ETD")
        self.mode = _Value("SecondaryElectrons")
        self.contrast = _Value(0.5)
        self.brightness = _Value(0.5)


class FakeSdbClient:
    """Stand-in for Autoscript's microscope client; connects to nothing."""

    #: coordinate system the stage reports positions in until told otherwise
    initial_coordinate_system = "Raw"

    def __init__(self) -> None:
        self.beams = _Beams()
        self.specimen = _Specimen(self.initial_coordinate_system)
        self.imaging = _Imaging()
        self.auto_functions = _AutoFunctions()
        self.detector = _Detector()

    def connect(self, host: str, port: int | None = None) -> None:
        self.host = host
        self.port = port
