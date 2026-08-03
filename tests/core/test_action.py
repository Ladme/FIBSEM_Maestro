# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from pathlib import Path

import numpy as np
from fibsem_maestro.core.action import Action
from fibsem_maestro.core.slice import SliceContext

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.props.memory import MemoryPropsStore
from fibsem_maestro.store.props.props_store import PropsStore


class ConcreteAction(Action):
    """Minimal concrete Action subclass for testing."""

    def __init__(
        self,
        microscope: Microscope,
        props_store: MemoryPropsStore,
        txt_log: MemoryTextLogger,
    ) -> None:
        self._microscope = microscope
        self._props_store = props_store
        self._txt_log = txt_log

    @property
    def name(self) -> str:
        return "test_action"

    @property
    def props_file(self) -> str:
        return "props.yaml"

    @property
    def props_store(self) -> PropsStore:
        return self._props_store

    @property
    def beam_type(self) -> BeamType:
        return BeamType.ELECTRON

    @property
    def props_to_collect(self) -> PropertyNames:
        return PropertyNames()

    @property
    def microscope(self) -> Microscope:
        return self._microscope

    @property
    def txt_log(self) -> TextLogger:
        return self._txt_log


def _make_global_properties() -> GlobalProperties:
    return GlobalProperties(
        electron_beam=BeamProperties(
            working_distance=5_000_000.0,
            pixel_size=2.0,
            detector_brightness=0.5,
            detector_contrast=0.5,
        )
    )


def _make_action() -> ConcreteAction:
    txt_log = MemoryTextLogger()
    microscope_settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0.0,
    )
    microscope = Microscope(microscope_settings, txt_log)
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    props_store = MemoryPropsStore(ctx)
    props_store.write("props.yaml", _make_global_properties())
    return ConcreteAction(microscope, props_store, txt_log)


def test_read_and_set_properties_reads_from_own_store_by_default():
    action = _make_action()
    props = GlobalProperties(
        electron_beam=BeamProperties(working_distance=7_000_000.0),
        microscope=None,
        ion_beam=None,
    )
    action._props_store.write("props.yaml", props)

    action.read_and_set_properties()

    assert np.isclose(action.microscope.beam.working_distance, 7_000_000.0)


def test_read_and_set_properties_reads_from_given_store():
    action = _make_action()
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    alternate_store = MemoryPropsStore(ctx)
    props = GlobalProperties(electron_beam=BeamProperties(working_distance=8_000_000.0))
    alternate_store.write("props.yaml", props)

    action.read_and_set_properties(alternate_store)

    assert np.isclose(action.microscope.beam.working_distance, 8_000_000.0)


def test_read_and_set_properties_applies_properties_to_microscope():
    action = _make_action()
    props = GlobalProperties(electron_beam=BeamProperties(working_distance=9_000_000.0))
    action._props_store.write("props.yaml", props)

    action.read_and_set_properties()

    assert np.isclose(action.microscope.beam.working_distance, 9_000_000.0)


def test_collect_and_write_properties_writes_to_own_store_by_default():
    action = _make_action()

    action.collect_and_write_properties()

    assert action._props_store.exists("props.yaml")


def test_collect_and_write_properties_writes_to_given_store():
    action = _make_action()
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    alternate_store = MemoryPropsStore(ctx)

    action.collect_and_write_properties(alternate_store)

    assert alternate_store.exists("props.yaml")


def test_read_properties_returns_stored_properties():
    action = _make_action()
    props = _make_global_properties()
    action._props_store.write("props.yaml", props)

    result = action.read_properties()

    assert result.electron_beam is not None
    assert result.electron_beam.working_distance is not None
    assert props.electron_beam is not None
    assert props.electron_beam.working_distance is not None

    assert np.isclose(
        result.electron_beam.working_distance,
        props.electron_beam.working_distance,
    )


def test_read_properties_reads_from_given_store():
    action = _make_action()
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    alternate_store = MemoryPropsStore(ctx)
    props = _make_global_properties()
    alternate_store.write("props.yaml", props)

    result = action.read_properties(alternate_store)

    assert result.electron_beam is not None
    assert result.electron_beam.working_distance is not None
    assert props.electron_beam is not None
    assert props.electron_beam.working_distance is not None

    assert np.isclose(
        result.electron_beam.working_distance,
        props.electron_beam.working_distance,
    )


def test_write_properties_writes_to_own_store_by_default():
    action = _make_action()
    props = _make_global_properties()

    action.write_properties(props)

    result = action._props_store.read("props.yaml")

    assert result.electron_beam is not None
    assert result.electron_beam.working_distance is not None
    assert props.electron_beam is not None
    assert props.electron_beam.working_distance is not None

    assert np.isclose(
        result.electron_beam.working_distance,
        props.electron_beam.working_distance,
    )


def test_write_properties_writes_to_given_store():
    action = _make_action()
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    alternate_store = MemoryPropsStore(ctx)
    props = _make_global_properties()

    action.write_properties(props, alternate_store)

    assert alternate_store.exists("props.yaml")
    result = alternate_store.read("props.yaml")

    assert result.electron_beam is not None
    assert result.electron_beam.working_distance is not None
    assert props.electron_beam is not None
    assert props.electron_beam.working_distance is not None

    assert np.isclose(
        result.electron_beam.working_distance,
        props.electron_beam.working_distance,
    )
