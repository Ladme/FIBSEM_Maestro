# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from pathlib import Path

import numpy as np
import pytest
import tifffile

from fibsem_maestro.core.image import Image, ImageError
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.store.image.file import FileImageStore


class SliceCursor:
    """Mutable stand-in for the run loop's slice pointer; `SliceView` is immutable."""

    def __init__(self, action_dir: Path, slice_index: int = 0) -> None:
        self._action_dir = action_dir
        self._view = SliceView(action_dir, slice_index)

    def __call__(self) -> SliceView:
        return self._view

    def advance_to(self, slice_index: int) -> None:
        self._view = SliceView(self._action_dir, slice_index)

    def dir(self, slice_index: int) -> Path:
        return SliceView(self._action_dir, slice_index).path()

    @property
    def action_dir(self) -> Path:
        return self._action_dir


@pytest.fixture
def cursor(tmp_path: Path) -> SliceCursor:
    return SliceCursor(tmp_path)


@pytest.fixture
def store(cursor: SliceCursor) -> FileImageStore[Image]:
    return FileImageStore(cursor, Image)


@pytest.fixture
def image() -> Image:
    return Image(np.arange(64, dtype=np.uint16).reshape(8, 8), pixel_size=2.5)


def test_write_appends_the_tif_extension(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift", image)

    assert [p.name for p in cursor.dir(0).iterdir()] == ["drift.tif"]


def test_write_keeps_an_existing_tif_extension(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift.tif", image)

    assert [p.name for p in cursor.dir(0).iterdir()] == ["drift.tif"]


def test_bare_and_suffixed_names_address_the_same_file(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift", image)

    assert store.exists("drift.tif") is True
    assert np.array_equal(store.read("drift.tif"), image)


def test_another_image_extension_is_replaced(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift.png", image)

    assert [p.name for p in cursor.dir(0).iterdir()] == ["drift.tif"]


def test_extension_matching_is_case_insensitive(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift.TIF", image)

    assert [p.name for p in cursor.dir(0).iterdir()] == ["drift.tif"]


def test_a_dot_in_the_name_is_not_mistaken_for_an_extension(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    """Only known image suffixes are stripped, so `v1.5_scan` keeps its name."""
    store.write("v1.5_scan", image)

    assert [p.name for p in cursor.dir(0).iterdir()] == ["v1.5_scan.tif"]


def test_names_differing_only_in_extension_collapse_onto_one_file(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift.png", image)
    store.write("drift.tif", image)

    assert [p.name for p in cursor.dir(0).iterdir()] == ["drift.tif"]


def test_write_places_the_file_in_the_slice_directory(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift", image)

    assert (cursor.dir(0) / "drift.tif").is_file()


def test_write_creates_the_slice_directory(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    assert not (cursor.action_dir / "slice_0000").exists()

    store.write("drift", image)

    assert (cursor.action_dir / "slice_0000").is_dir()


def test_write_overwrites_an_existing_file(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift", image)
    store.write("drift", Image(np.zeros((2, 2), dtype=np.uint16), pixel_size=9.0))

    assert store.read("drift").shape == (2, 2)


def test_write_follows_the_slice(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift", image)
    cursor.advance_to(1)
    store.write("drift", image)

    assert (cursor.dir(0) / "drift.tif").is_file()
    assert (cursor.dir(1) / "drift.tif").is_file()


def test_write_keeps_distinct_filenames_apart(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("before", image)
    store.write("after", image)

    assert sorted(p.name for p in cursor.dir(0).iterdir()) == [
        "after.tif",
        "before.tif",
    ]


def test_exists_is_false_before_writing(store: FileImageStore[Image]) -> None:
    assert store.exists("drift") is False


def test_exists_is_true_after_writing(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift", image)

    assert store.exists("drift") is True


def test_exists_normalises_the_filename(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift.tif", image)

    assert store.exists("drift") is True


def test_exists_is_per_slice(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift", image)
    cursor.advance_to(1)

    assert store.exists("drift") is False


def test_exists_does_not_create_the_slice_directory(
    store: FileImageStore[Image], cursor: SliceCursor
) -> None:
    """A query must leave no trace; only writes create directories."""
    store.exists("drift")

    assert not (cursor.action_dir / "slice_0000").exists()


def test_read_returns_the_written_pixels(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift", image)

    assert np.array_equal(store.read("drift"), image)


def test_read_preserves_the_pixel_size(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift", image)

    assert store.read("drift").pixel_size == pytest.approx(2.5)


def test_read_preserves_the_dtype(store: FileImageStore[Image], image: Image) -> None:
    store.write("drift", image)

    assert store.read("drift").dtype == np.uint16


def test_read_raises_when_the_file_is_missing(store: FileImageStore[Image]) -> None:
    with pytest.raises(FileNotFoundError, match="No image found"):
        store.read("drift")


def test_read_error_names_the_expected_path(store: FileImageStore[Image]) -> None:
    with pytest.raises(FileNotFoundError, match="drift.tif"):
        store.read("drift")


def test_read_is_per_slice(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift", image)
    cursor.advance_to(1)

    with pytest.raises(FileNotFoundError):
        store.read("drift")


def test_read_does_not_consume_the_file(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift", image)

    store.read("drift")

    assert store.exists("drift") is True


def test_read_closes_the_file(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    """Windows blocks deletion while a handle is open."""
    store.write("drift", image)

    store.read("drift")
    (cursor.dir(0) / "drift.tif").unlink()

    assert store.exists("drift") is False


def test_read_raises_for_a_tif_without_pixel_size(
    store: FileImageStore[Image], cursor: SliceCursor
) -> None:
    """A TIF from another tool has no ImageJ pixel size; `from_tiff` rejects it."""
    tifffile.imwrite(cursor.dir(0) / "foreign.tif", np.ones((4, 4), dtype=np.uint16))

    with pytest.raises(ImageError):
        store.read("foreign")


def test_read_does_not_create_the_slice_directory(
    store: FileImageStore[Image], cursor: SliceCursor
) -> None:
    with pytest.raises(FileNotFoundError):
        store.read("drift")

    assert not (cursor.action_dir / "slice_0000").exists()


def test_copy_to_places_the_file_in_the_target_slice(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift", image)

    store.copy_to("drift", store.at(3))

    assert (cursor.dir(3) / "drift.tif").is_file()


def test_copy_to_leaves_the_source_in_place(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift", image)

    store.copy_to("drift", store.at(3))

    assert store.exists("drift") is True


def test_copy_to_preserves_pixels_and_pixel_size(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift", image)

    store.copy_to("drift", store.at(3))

    copied = store.at(3).read("drift")
    assert np.array_equal(copied, image)
    assert copied.pixel_size == pytest.approx(2.5)


def test_copy_to_normalises_the_filename(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift", image)

    store.copy_to("drift.tif", store.at(3))

    assert (cursor.dir(3) / "drift.tif").is_file()


def test_copy_to_raises_when_the_source_is_missing(
    store: FileImageStore[Image],
) -> None:
    with pytest.raises(FileNotFoundError, match="No image found"):
        store.copy_to("drift", store.at(3))


def test_copy_to_overwrites_an_existing_target(
    store: FileImageStore[Image], image: Image
) -> None:
    target = store.at(3)
    target.write("drift", Image(np.zeros((2, 2), dtype=np.uint16), pixel_size=9.0))
    store.write("drift", image)

    store.copy_to("drift", target)

    assert target.read("drift").shape == (8, 8)


def test_copy_to_creates_the_target_slice_directory(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.write("drift", image)
    assert not (cursor.action_dir / "slice_0003").exists()

    store.copy_to("drift", store.at(3))

    assert (cursor.action_dir / "slice_0003").is_dir()


def test_copy_to_a_store_in_another_action(
    store: FileImageStore[Image], tmp_path: Path, image: Image
) -> None:
    other = FileImageStore(SliceCursor(tmp_path / "other"), Image)
    store.write("drift", image)

    store.copy_to("drift", other)

    assert np.array_equal(other.read("drift"), image)


def test_copy_to_the_same_slice_is_a_no_op(
    store: FileImageStore[Image], image: Image
) -> None:
    """A self-copy must neither raise nor truncate the file."""
    store.write("drift", image)

    store.copy_to("drift", store)

    assert np.array_equal(store.read("drift"), image)


def test_copy_to_an_equivalent_view_of_the_same_slice_is_a_no_op(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift", image)

    store.copy_to("drift", store.at(0))

    assert np.array_equal(store.read("drift"), image)


def test_copy_to_preserves_the_image_class(
    store: FileImageStore[Image], image: Image
) -> None:
    store.write("drift", image)

    store.copy_to("drift", store.at(3))

    assert type(store.at(3).read("drift")) is Image


def test_slice_reports_the_current_index(
    store: FileImageStore[Image], cursor: SliceCursor
) -> None:
    assert store.slice == 0

    cursor.advance_to(7)

    assert store.slice == 7


def test_at_addresses_the_requested_slice(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.at(5).write("drift", image)

    assert (cursor.dir(5) / "drift.tif").is_file()


def test_at_reports_the_requested_slice(store: FileImageStore[Image]) -> None:
    assert store.at(5).slice == 5


def test_at_does_not_move_the_original_store(
    store: FileImageStore[Image], image: Image
) -> None:
    store.at(5).write("drift", image)

    assert store.slice == 0
    assert store.exists("drift") is False


def test_at_is_pinned_when_the_run_advances(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    pinned = store.at(3)

    cursor.advance_to(9)
    pinned.write("drift", image)

    assert (cursor.dir(3) / "drift.tif").is_file()


def test_at_rejects_a_negative_slice(store: FileImageStore[Image]) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        store.at(-1)


def test_next_addresses_the_following_slice(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.next.write("drift", image)

    assert (cursor.dir(1) / "drift.tif").is_file()


def test_next_is_relative_to_the_current_slice(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    cursor.advance_to(4)

    store.next.write("drift", image)

    assert (cursor.dir(5) / "drift.tif").is_file()


def test_next_reports_the_following_slice(
    store: FileImageStore[Image], cursor: SliceCursor
) -> None:
    cursor.advance_to(2)

    assert store.next.slice == 3


def test_next_is_pinned_at_access_time(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    view = store.next

    cursor.advance_to(9)
    view.write("drift", image)

    assert (cursor.dir(1) / "drift.tif").is_file()


def test_next_keeps_the_image_class(store: FileImageStore[Image], image: Image) -> None:
    store.next.write("drift", image)

    assert type(store.next.read("drift")) is Image


def test_next_of_next_advances_twice(
    store: FileImageStore[Image], cursor: SliceCursor, image: Image
) -> None:
    store.next.next.write("drift", image)

    assert (cursor.dir(2) / "drift.tif").is_file()
