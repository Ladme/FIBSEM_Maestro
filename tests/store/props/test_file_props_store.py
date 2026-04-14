# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path

from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.store.props.file import FilePropsStore


def _make_props() -> GlobalProperties:
    return GlobalProperties(
        microscope=None,
        electron_beam=BeamProperties(working_distance=5000.0, pixel_size=2.0),
        ion_beam=BeamProperties(detector_contrast=0.4),
    )


def test_file_props_store_exists_returns_false_when_file_does_not_exist(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FilePropsStore(ctx)

    assert store.exists("props.yaml") is False


def test_file_props_store_write_and_read_roundtrip(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FilePropsStore(ctx)
    props = _make_props()
    assert props.electron_beam is not None
    assert props.ion_beam is not None

    store.write("props.yaml", props)
    result = store.read("props.yaml")

    assert result.electron_beam is not None
    assert result.ion_beam is not None
    assert result.microscope is None
    assert result.electron_beam.working_distance == props.electron_beam.working_distance
    assert result.electron_beam.pixel_size == props.electron_beam.pixel_size
    assert result.ion_beam.detector_contrast == props.ion_beam.detector_contrast


def test_file_props_store_exists_returns_true_after_write(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FilePropsStore(ctx)

    store.write("props.yaml", _make_props())

    assert store.exists("props.yaml") is True


def test_file_props_store_slice_returns_current_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=5)
    store = FilePropsStore(ctx)

    assert store.slice == 5


def test_file_props_store_slice_returns_none_when_slice_is_none(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path)
    store = FilePropsStore(ctx)

    assert store.slice is None


def test_file_props_store_at_writes_and_reads_from_given_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FilePropsStore(ctx)

    store.at(4).write("props.yaml", _make_props())

    assert store.at(4).exists("props.yaml") is True
    assert not store.exists("props.yaml")


def test_file_props_store_next_writes_and_reads_from_next_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=2)
    store = FilePropsStore(ctx)

    store.next.write("props.yaml", _make_props())
    result = store.next.read("props.yaml")

    assert result.electron_beam is not None
    assert (
        result.electron_beam.working_distance
        == _make_props().electron_beam.working_distance  # type: ignore
    )
    assert not store.exists("props.yaml")


def test_file_props_store_reflects_incremented_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FilePropsStore(ctx)

    store.write("props.yaml", _make_props())
    ctx.increment()

    assert not store.exists("props.yaml")
    assert store.at(0).exists("props.yaml") is True
