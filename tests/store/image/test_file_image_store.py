# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path

import numpy as np
from fibsem_maestro.core.slice import SliceContext

from fibsem_maestro.core.image import Image
from fibsem_maestro.store.image.file import FileImageStore
from fibsem_maestro.store.image.image_store import normalize_tif


def test_normalize_tif_adds_tif_extension_when_missing():
    assert normalize_tif("myfile") == "myfile.tif"


def test_normalize_tif_leaves_filename_unchanged_when_already_has_tif():
    assert normalize_tif("myfile.tif") == "myfile.tif"


def test_normalize_tif_does_not_double_add_extension():
    assert normalize_tif("myfile.tif").endswith(".tif")
    assert normalize_tif("myfile.tif").count(".tif") == 1


def test_file_image_store_exists_returns_false_when_file_does_not_exist(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileImageStore(ctx, Image, Path("images"))

    assert store.exists("frame") is False


def test_file_image_store_write_and_read_roundtrip(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileImageStore(ctx, Image, Path("images"))
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.uint16), pixel_size=2.0)

    store.write("frame", img)
    result = store.read("frame")

    assert np.array_equal(result, img)
    assert np.isclose(result.pixel_size, img.pixel_size)


def test_file_image_store_exists_returns_true_after_write(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileImageStore(ctx, Image, Path("images"))
    img = Image(np.zeros((64, 64), dtype=np.uint16), pixel_size=2.0)

    store.write("frame", img)

    assert store.exists("frame") is True


def test_file_image_store_write_normalizes_filename(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileImageStore(ctx, Image, Path("images"))
    img = Image(np.zeros((64, 64), dtype=np.uint16), pixel_size=2.0)

    store.write("frame", img)

    assert store.exists("frame.tif") is True


def test_file_image_store_slice_returns_current_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=5)
    store = FileImageStore(ctx, Image, Path("images"))

    assert store.slice == 5


def test_file_image_store_slice_returns_none_when_slice_is_none(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path)
    store = FileImageStore(ctx, Image, Path("images"))

    assert store.slice is None


def test_file_image_store_at_reads_from_given_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileImageStore(ctx, Image, Path("images"))
    img = Image(np.zeros((64, 64), dtype=np.uint16), pixel_size=2.0)

    # write at slice 3
    store.at(3).write("frame", img)

    # read back at slice 3 from a fresh context still on slice 0
    assert store.at(3).exists("frame") is True
    assert not store.exists("frame")


def test_file_image_store_next_reads_from_next_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=2)
    store = FileImageStore(ctx, Image, Path("images"))
    img = Image(np.zeros((64, 64), dtype=np.uint16), pixel_size=2.0)

    store.next.write("frame", img)
    result = store.next.read("frame")

    assert np.array_equal(result, img)
    assert not store.exists("frame")


def test_file_image_store_reflects_incremented_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileImageStore(ctx, Image, Path("images"))
    img = Image(np.zeros((64, 64), dtype=np.uint16), pixel_size=2.0)

    store.write("frame", img)
    ctx.increment()

    # after increment the store should point to slice 1, not slice 0
    assert not store.exists("frame")
    assert store.at(0).exists("frame") is True
