import pytest

from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.sweeping_settings import SweepingSettings

pytest.importorskip("autoscript_sdb_microscope_client")

from autoscript_fakes import FakeSdbClient

from fibsem_maestro.microscope.autoscript_control import (
    microscope_control as autoscript_microscope_control,
)


@pytest.fixture
def fake_client(monkeypatch: pytest.MonkeyPatch) -> FakeSdbClient:
    """The client the Autoscript control will connect through."""
    client = FakeSdbClient()
    monkeypatch.setattr(
        autoscript_microscope_control, "SdbMicroscopeClient", lambda: client
    )
    return client


@pytest.fixture
def autoscript_microscope(fake_client: FakeSdbClient) -> Microscope:
    _ = fake_client  # connects through the fake
    return Microscope(
        MicroscopeSettings(control="autoscript", ip_address="localhost"),
        MemoryTextLogger(lambda: 0),
    )


def test_ion_beam_working_distance_can_be_swept(
    autoscript_microscope: Microscope,
) -> None:
    sweeping = Sweeping(
        autoscript_microscope.ion_beam,
        SweepingSettings(range=(-1000.0, 1000.0), steps=3),
        "working_distance",
        MemoryTextLogger(lambda: 0),
    )
    assert len(list(sweeping.sweep())) == 3


def test_sweep_values_outside_instrument_limits_are_skipped(
    autoscript_microscope: Microscope,
) -> None:
    # the fake ion beam allows 1-60 mm; 16.5 mm +- 50 mm leaves one valid value
    sweeping = Sweeping(
        autoscript_microscope.ion_beam,
        SweepingSettings(range=(-50e6, 50e6), steps=3),
        "working_distance",
        MemoryTextLogger(lambda: 0),
    )
    assert [s.value for s in sweeping.sweep()] == pytest.approx([16.5e6])


def test_autoscript_reapplying_pixel_size_keeps_standard_resolution(
    autoscript_microscope: Microscope, fake_client: FakeSdbClient
) -> None:
    beam = autoscript_microscope.electron_beam
    beam.resolution = Resolution(1024, 884)
    fake_client.beams.electron_beam.horizontal_field_width.value = 1192.7193611970083e-9

    beam.pixel_size = beam.pixel_size

    assert beam.resolution == Resolution(1024, 884)
    assert fake_client.beams.electron_beam.scanning.resolution.value == "1024x884"
