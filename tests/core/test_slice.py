# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path

from fibsem_maestro.core.slice import SliceContext, SliceView


def test_slice_view_dir_returns_root_dir_when_slice_index_is_none(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=None)

    assert view.dir() == tmp_path


def test_slice_view_dir_returns_slice_subdir_when_slice_index_is_set(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=3)

    assert view.dir() == tmp_path / "slice_0003"


def test_slice_view_dir_creates_directory(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=5)

    view.dir()

    assert (tmp_path / "slice_0005").is_dir()


def test_slice_view_images_returns_images_subdir(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=1)

    assert view.images() == tmp_path / "slice_0001" / "images"


def test_slice_view_images_creates_directory(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=1)

    view.images()

    assert (tmp_path / "slice_0001" / "images").is_dir()


def test_slice_view_props_returns_props_subdir(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=2)

    assert view.props() == tmp_path / "slice_0002" / "props"


def test_slice_view_props_creates_directory(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=2)

    view.props()

    assert (tmp_path / "slice_0002" / "props").is_dir()


def test_slice_view_custom_returns_named_subdir(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=0)

    assert view.custom("mydir") == tmp_path / "slice_0000" / "mydir"


def test_slice_view_custom_creates_directory(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=0)

    view.custom("mydir")

    assert (tmp_path / "slice_0000" / "mydir").is_dir()


def test_slice_view_logs_returns_log_file_path(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=7)

    assert view.logs() == tmp_path / "slice_0007" / "app.log"


def test_slice_view_logs_does_not_create_log_file(tmp_path: Path):
    view = SliceView(root_dir=tmp_path, slice_index=7)

    view.logs()

    assert not (tmp_path / "slice_0007" / "app.log").exists()


def test_slice_context_current_slice_is_none_by_default(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path)

    assert ctx.current_slice is None


def test_slice_context_current_returns_root_view_when_slice_is_none(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path)

    assert ctx.current.slice_index is None
    assert ctx.current.root_dir == tmp_path


def test_slice_context_current_returns_view_for_current_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=3)

    assert ctx.current.slice_index == 3


def test_slice_context_next_returns_view_for_next_slice(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=3)

    assert ctx.next.slice_index == 4


def test_slice_context_next_returns_root_view_when_slice_is_none(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path)

    assert ctx.next.slice_index is None


def test_slice_context_root_returns_view_with_none_slice_index(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=5)

    assert ctx.root.slice_index is None
    assert ctx.root.root_dir == tmp_path


def test_slice_context_at_returns_view_for_given_index(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=0)

    assert ctx.at(7).slice_index == 7


def test_slice_context_increment_advances_slice_by_one(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=2)

    ctx.increment()

    assert ctx.current_slice == 3


def test_slice_context_increment_does_nothing_when_slice_is_none(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path)

    ctx.increment()

    assert ctx.current_slice is None


def test_slice_context_dir_delegates_to_current(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=4)

    assert ctx.dir() == ctx.current.dir()


def test_slice_context_images_delegates_to_current(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=4)

    assert ctx.images() == ctx.current.images()


def test_slice_context_props_delegates_to_current(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=4)

    assert ctx.props() == ctx.current.props()


def test_slice_context_custom_delegates_to_current(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=4)

    assert ctx.custom("mydir") == ctx.current.custom("mydir")


def test_slice_context_logs_delegates_to_current(tmp_path: Path):
    ctx = SliceContext(root_dir=tmp_path, current_slice=4)

    assert ctx.logs() == ctx.current.logs()
