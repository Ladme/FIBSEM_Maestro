# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from pathlib import Path

import pytest

from fibsem_maestro.slice.slice_view import SliceView


@pytest.fixture
def view(tmp_path: Path) -> SliceView:
    return SliceView(tmp_path, 0)


def test_slice_index_returns_the_constructor_value(tmp_path: Path) -> None:
    assert SliceView(tmp_path, 42).slice_index == 42


def test_action_dir_returns_the_constructor_value(tmp_path: Path) -> None:
    assert SliceView(tmp_path, 0).action_dir == tmp_path


def test_path_is_named_from_the_slice_index(view: SliceView) -> None:
    assert view.path().name == "slice_0000"


def test_path_is_under_the_action_directory(tmp_path: Path) -> None:
    view = SliceView(tmp_path / "milling", 7)

    assert view.path().parent == tmp_path / "milling"


def test_path_pads_the_index_to_four_digits(tmp_path: Path) -> None:
    assert SliceView(tmp_path, 7).path().name == "slice_0007"
    assert SliceView(tmp_path, 42).path().name == "slice_0042"
    assert SliceView(tmp_path, 9999).path().name == "slice_9999"


def test_path_does_not_truncate_indices_above_four_digits(tmp_path: Path) -> None:
    assert SliceView(tmp_path, 12345).path().name == "slice_12345"


def test_path_creates_the_directory(tmp_path: Path) -> None:
    view = SliceView(tmp_path / "milling", 3)

    assert view.path().is_dir()


def test_path_creates_missing_parents(tmp_path: Path) -> None:
    view = SliceView(tmp_path / "run" / "milling", 3)

    assert view.path().is_dir()


def test_path_is_idempotent(view: SliceView) -> None:
    first = view.path()
    second = view.path()

    assert first == second
    assert second.is_dir()


def test_path_does_not_clear_an_existing_directory(tmp_path: Path) -> None:
    """Re-addressing a slice must not destroy images already written there."""
    view = SliceView(tmp_path, 3)
    (view.path() / "drift.png").write_text("image")

    assert (view.path() / "drift.png").read_text() == "image"


def test_two_views_on_the_same_slice_resolve_to_one_directory(tmp_path: Path) -> None:
    assert SliceView(tmp_path, 3).path() == SliceView(tmp_path, 3).path()


def test_different_slices_resolve_to_different_directories(tmp_path: Path) -> None:
    assert SliceView(tmp_path, 3).path() != SliceView(tmp_path, 4).path()


def test_same_index_under_different_actions_resolve_separately(tmp_path: Path) -> None:
    milling = SliceView(tmp_path / "milling", 3).path()
    imaging = SliceView(tmp_path / "imaging", 3).path()

    assert milling != imaging
    assert milling.name == imaging.name


def test_path_accepts_a_zero_index(tmp_path: Path) -> None:
    assert SliceView(tmp_path, 0).path().name == "slice_0000"


def test_view_does_not_touch_the_filesystem_before_access(tmp_path: Path) -> None:
    target = tmp_path / "milling"

    SliceView(target, 3)

    assert not target.exists()


def test_negative_slice_index_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        SliceView(tmp_path, -1)


def test_rejection_names_the_offending_index(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="got -5"):
        SliceView(tmp_path, -5)


def test_negative_slice_index_is_rejected_before_touching_the_filesystem(
    tmp_path: Path,
) -> None:
    target = tmp_path / "milling"

    with pytest.raises(ValueError):
        SliceView(target, -1)

    assert not target.exists()


def test_action_dir_does_not_create_the_directory(tmp_path: Path) -> None:
    target = tmp_path / "milling"

    assert SliceView(target, 0).action_dir == target
    assert not target.exists()


def test_expected_path_names_the_slice_folder(tmp_path: Path) -> None:
    assert SliceView(tmp_path, 42).expected_path == tmp_path / "slice_0042"


def test_expected_path_does_not_create_anything(tmp_path: Path) -> None:
    view = SliceView(tmp_path / "milling", 3)

    view.expected_path

    assert not (tmp_path / "milling").exists()


def test_path_creates_what_directory_only_names(tmp_path: Path) -> None:
    view = SliceView(tmp_path / "milling", 3)

    assert view.path() == view.expected_path
    assert view.expected_path.is_dir()
