# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from pathlib import Path

import numpy as np
import pytest
from fibsem_maestro.core.slice import SliceContext

from fibsem_maestro.core.image import Image
from fibsem_maestro.store.frame.file import FileFrameStore


def test_path_returns_correct_tif_filename_for_current_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=3)
    store = FileFrameStore(ctx, tmp_path / "frames")

    assert store.path() == tmp_path / "frames" / "slice_0003.tif"


def test_path_creates_directory_if_not_exists(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=1)
    store = FileFrameStore(ctx, tmp_path / "frames")

    store.path()

    assert (tmp_path / "frames").is_dir()


def test_save_to_memory_always_raises_runtime_error(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileFrameStore(ctx, tmp_path / "frames")
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)

    with pytest.raises(RuntimeError):
        store.save_to_memory(img)


def test_exists_returns_false_when_file_does_not_exist(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileFrameStore(ctx, tmp_path / "frames")

    assert store.exists() is False


def test_exists_returns_true_when_file_exists(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileFrameStore(ctx, tmp_path / "frames")
    store.path().touch()

    assert store.exists() is True


def test_raise_if_exists_does_not_raise_when_file_does_not_exist(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileFrameStore(ctx, tmp_path / "frames")

    store.raise_if_exists(RuntimeError)


def test_raise_if_exists_raises_given_exception_when_file_exists(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileFrameStore(ctx, tmp_path / "frames")
    store.path().touch()

    with pytest.raises(FileExistsError):
        store.raise_if_exists(FileExistsError)


def test_raise_if_exists_message_contains_slice_index(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=5)
    store = FileFrameStore(ctx, tmp_path / "frames")
    store.path().touch()

    with pytest.raises(RuntimeError, match="5"):
        store.raise_if_exists(RuntimeError)


def test_slice_property_returns_current_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=7)
    store = FileFrameStore(ctx, tmp_path / "frames")

    assert store.slice == 7


def test_slice_property_returns_none_when_slice_is_none(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path)
    store = FileFrameStore(ctx, tmp_path / "frames")

    assert store.slice is None


def test_path_reflects_updated_slice_after_increment(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)
    store = FileFrameStore(ctx, tmp_path / "frames")

    ctx.increment()

    assert store.path() == tmp_path / "frames" / "slice_0001.tif"
