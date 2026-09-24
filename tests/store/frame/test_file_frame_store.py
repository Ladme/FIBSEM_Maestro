# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from pathlib import Path

import numpy as np
import pytest

from fibsem_maestro.core.format import ImageFormat
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.provenance import Provenance
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.store.frame.file import FileFrameStore


class SliceCursor:
    """Mutable stand-in for the run loop's slice pointer; `SliceView` is immutable."""

    def __init__(self, action_dir: Path, slice_index: int = 0) -> None:
        self._action_dir = action_dir
        self._view = SliceView(action_dir, slice_index)

    def __call__(self) -> SliceView:
        return self._view

    def advance_to(self, slice_index: int) -> None:
        self._view = SliceView(self._action_dir, slice_index)

    @property
    def action_dir(self) -> Path:
        return self._action_dir


@pytest.fixture
def cursor(tmp_path: Path) -> SliceCursor:
    return SliceCursor(tmp_path)


@pytest.fixture
def store(cursor: SliceCursor) -> FileFrameStore:
    return FileFrameStore(cursor)


@pytest.fixture
def frame() -> Image:
    return Image(np.arange(64, dtype=np.uint16).reshape(8, 8), pixel_size=2.5)


def write(store: FileFrameStore, frame: Image) -> None:
    """Stand in for the microscope layer writing to the path the store handed out."""
    frame.save(store.path(), ImageFormat.TIF)


def test_path_is_named_from_the_slice_index(store: FileFrameStore) -> None:
    assert store.path().name == "slice_0000.tif"


def test_path_pads_the_index_to_four_digits(
    store: FileFrameStore, cursor: SliceCursor
) -> None:
    cursor.advance_to(42)

    assert store.path().name == "slice_0042.tif"


def test_path_is_flat_not_inside_the_slice_directory(
    store: FileFrameStore, cursor: SliceCursor
) -> None:
    """Frames live in one directory with the index in the filename."""
    assert store.path().parent == cursor.action_dir / "frames"


def test_path_uses_the_default_directory_name(store: FileFrameStore) -> None:
    assert store.path().parent.name == "frames"


def test_path_honours_a_custom_directory_name(cursor: SliceCursor) -> None:
    store = FileFrameStore(cursor, directory_name="raw")

    assert store.path().parent.name == "raw"


def test_path_creates_the_frames_directory(
    store: FileFrameStore, cursor: SliceCursor
) -> None:
    assert not (cursor.action_dir / "frames").exists()

    store.path()

    assert (cursor.action_dir / "frames").is_dir()


def test_path_does_not_create_the_slice_directory(
    store: FileFrameStore, cursor: SliceCursor
) -> None:
    store.path()

    assert not (cursor.action_dir / "slice_0000").exists()


def test_path_does_not_create_the_frame_file(store: FileFrameStore) -> None:
    assert not store.path().exists()


def test_path_is_never_none(store: FileFrameStore) -> None:
    """The contract with `grab_frame`: a Path means write straight to disk."""
    assert store.path() is not None


def test_path_follows_the_slice(store: FileFrameStore, cursor: SliceCursor) -> None:
    assert store.path().name == "slice_0000.tif"

    cursor.advance_to(5)

    assert store.path().name == "slice_0005.tif"


def test_different_slices_map_to_different_paths(store: FileFrameStore) -> None:
    assert store.at(1).path() != store.at(2).path()


def test_save_to_memory_raises(store: FileFrameStore, frame: Image) -> None:
    """`path()` never returns None here, so reaching this method is a caller bug."""
    with pytest.raises(RuntimeError, match="should never be called"):
        store.save_to_memory(frame)


def test_save_to_memory_does_not_write_anything(
    store: FileFrameStore, frame: Image
) -> None:
    with pytest.raises(RuntimeError):
        store.save_to_memory(frame)

    assert not store.exists()


def test_exists_is_false_before_anything_is_written(store: FileFrameStore) -> None:
    assert store.exists() is False


def test_exists_is_true_after_a_frame_is_written(
    store: FileFrameStore, frame: Image
) -> None:
    write(store, frame)

    assert store.exists() is True


def test_exists_is_per_slice(
    store: FileFrameStore, cursor: SliceCursor, frame: Image
) -> None:
    write(store, frame)
    cursor.advance_to(1)

    assert store.exists() is False


def test_exists_does_not_create_the_frame_file(store: FileFrameStore) -> None:
    store.exists()

    assert not store.path().exists()


def test_read_returns_the_written_frame(store: FileFrameStore, frame: Image) -> None:
    write(store, frame)

    assert np.array_equal(store.read(Provenance.MAESTRO), frame)


def test_read_preserves_the_pixel_size(store: FileFrameStore, frame: Image) -> None:
    write(store, frame)

    assert store.read(Provenance.MAESTRO).pixel_size == pytest.approx(2.5)


def test_read_returns_an_image(store: FileFrameStore, frame: Image) -> None:
    write(store, frame)

    assert isinstance(store.read(Provenance.MAESTRO), Image)


def test_read_raises_when_no_frame_exists(store: FileFrameStore) -> None:
    with pytest.raises(FileNotFoundError, match="No frame found"):
        store.read(Provenance.MAESTRO)


def test_read_error_names_the_expected_path(store: FileFrameStore) -> None:
    with pytest.raises(FileNotFoundError, match="slice_0000.tif"):
        store.read(Provenance.MAESTRO)


def test_read_is_per_slice(
    store: FileFrameStore, cursor: SliceCursor, frame: Image
) -> None:
    write(store, frame)
    cursor.advance_to(1)

    with pytest.raises(FileNotFoundError):
        store.read(Provenance.MAESTRO)


def test_read_does_not_consume_the_frame(store: FileFrameStore, frame: Image) -> None:
    write(store, frame)

    store.read(Provenance.MAESTRO)

    assert store.exists() is True


def test_read_closes_the_file(store: FileFrameStore, frame: Image) -> None:
    """Windows blocks deletion while a handle is open."""
    write(store, frame)

    store.read(Provenance.MAESTRO)
    store.path().unlink()

    assert not store.exists()


def test_raise_if_exists_is_silent_when_absent(store: FileFrameStore) -> None:
    store.raise_if_exists(FileExistsError, "frame already acquired")


def test_raise_if_exists_raises_when_present(
    store: FileFrameStore, frame: Image
) -> None:
    write(store, frame)

    with pytest.raises(FileExistsError, match="frame already acquired"):
        store.raise_if_exists(FileExistsError, "frame already acquired")


def test_raise_if_exists_is_per_slice(
    store: FileFrameStore, cursor: SliceCursor, frame: Image
) -> None:
    write(store, frame)
    cursor.advance_to(1)

    store.raise_if_exists(FileExistsError, "frame already acquired")


def test_raise_if_exists_does_not_remove_the_frame(
    store: FileFrameStore, frame: Image
) -> None:
    write(store, frame)

    with pytest.raises(FileExistsError):
        store.raise_if_exists(FileExistsError, "x")

    assert store.exists() is True


def test_slice_reports_the_current_index(
    store: FileFrameStore, cursor: SliceCursor
) -> None:
    assert store.slice == 0

    cursor.advance_to(7)

    assert store.slice == 7


def test_at_addresses_the_requested_slice(store: FileFrameStore) -> None:
    assert store.at(5).path().name == "slice_0005.tif"


def test_at_reports_the_requested_slice(store: FileFrameStore) -> None:
    assert store.at(5).slice == 5


def test_at_does_not_move_the_original_store(store: FileFrameStore) -> None:
    store.at(5).path()

    assert store.slice == 0


def test_at_is_pinned_when_the_run_advances(
    store: FileFrameStore, cursor: SliceCursor
) -> None:
    pinned = store.at(3)

    cursor.advance_to(9)

    assert pinned.path().name == "slice_0003.tif"


def test_at_keeps_the_directory_name(cursor: SliceCursor) -> None:
    store = FileFrameStore(cursor, directory_name="raw")

    assert store.at(5).path().parent.name == "raw"


def test_at_reads_a_frame_written_through_the_view(
    store: FileFrameStore, frame: Image
) -> None:
    view = store.at(5)

    write(view, frame)

    assert store.at(5).exists() is True
    assert store.exists() is False


def test_at_rejects_a_negative_slice(store: FileFrameStore) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        store.at(-1)


def test_next_addresses_the_following_slice(store: FileFrameStore) -> None:
    assert store.next.path().name == "slice_0001.tif"


def test_next_is_relative_to_the_current_slice(
    store: FileFrameStore, cursor: SliceCursor
) -> None:
    cursor.advance_to(4)

    assert store.next.path().name == "slice_0005.tif"


def test_next_reports_the_following_slice(
    store: FileFrameStore, cursor: SliceCursor
) -> None:
    cursor.advance_to(2)

    assert store.next.slice == 3


def test_next_is_pinned_at_access_time(
    store: FileFrameStore, cursor: SliceCursor
) -> None:
    view = store.next

    cursor.advance_to(9)

    assert view.path().name == "slice_0001.tif"


def test_next_keeps_the_directory_name(cursor: SliceCursor) -> None:
    store = FileFrameStore(cursor, directory_name="raw")

    assert store.next.path().parent.name == "raw"


def test_next_of_next_advances_twice(store: FileFrameStore) -> None:
    assert store.next.next.path().name == "slice_0002.tif"
