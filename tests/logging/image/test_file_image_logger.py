# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest

from fibsem_maestro.core.point import Point
from fibsem_maestro.logging.image.file import FileImageLogger
from fibsem_maestro.logging.image.overlay import (
    HeatmapOverlay,
    Overlay,
    PolylineOverlay,
    RectangleOverlay,
    VerticalLineOverlay,
)
from fibsem_maestro.logging.image.plot_element import Curve, VerticalLine
from fibsem_maestro.slice.slice_view import SliceView


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

    def names(self, slice_index: int = 0) -> list[str]:
        return sorted(p.name for p in self.dir(slice_index).iterdir())


@pytest.fixture(autouse=True)
def no_leaked_figures() -> None:
    """pyplot's figure registry is global; start each test from a clean slate."""
    plt.close("all")


@pytest.fixture
def cursor(tmp_path: Path) -> SliceCursor:
    return SliceCursor(tmp_path)


@pytest.fixture
def logger(cursor: SliceCursor) -> FileImageLogger:
    return FileImageLogger(cursor)


@pytest.fixture
def image() -> np.ndarray:
    return np.arange(64, dtype=float).reshape(8, 8)


def is_png(path: Path) -> bool:
    return path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_save_image_writes_into_the_current_slice_directory(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image)

    assert cursor.names() == ["drift.png"]


def test_save_image_writes_a_valid_png(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image)

    assert is_png(cursor.dir(0) / "drift.png")


def test_save_image_creates_the_slice_directory(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image)

    assert cursor.dir(0).is_dir()


def test_save_image_accepts_a_title(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image, None, "slice 0 drift")

    assert is_png(cursor.dir(0) / "drift.png")


def test_save_image_follows_the_slice(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("zero.png", image)
    cursor.advance_to(1)
    logger.save_image("one.png", image)

    assert cursor.names(0) == ["zero.png"]
    assert cursor.names(1) == ["one.png"]


def test_save_image_closes_its_figure(
    logger: FileImageLogger, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image)

    assert plt.get_fignums() == []


def test_save_image_with_rectangle_overlay(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image, [RectangleOverlay(1.0, 1.0, 3.0, 3.0)])

    assert is_png(cursor.dir(0) / "drift.png")


def test_save_image_with_polyline_overlay(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    overlay = PolylineOverlay([Point(0.0, 0.0), Point(4.0, 4.0)])

    logger.save_image("drift.png", image, [overlay])

    assert is_png(cursor.dir(0) / "drift.png")


def test_save_image_with_empty_polyline_overlay(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image, [PolylineOverlay([])])

    assert is_png(cursor.dir(0) / "drift.png")


def test_save_image_with_vertical_line_overlay(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image, [VerticalLineOverlay(3.0)])

    assert is_png(cursor.dir(0) / "drift.png")


def test_save_image_with_heatmap_overlay(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image, [HeatmapOverlay(np.ones((8, 8)))])

    assert is_png(cursor.dir(0) / "drift.png")


def test_save_image_with_several_overlays(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image(
        "drift.png",
        image,
        [RectangleOverlay(1.0, 1.0, 2.0, 2.0), VerticalLineOverlay(3.0)],
    )

    assert is_png(cursor.dir(0) / "drift.png")


def test_save_image_rejects_unsupported_overlay_types(
    logger: FileImageLogger, image: np.ndarray
) -> None:
    """An overlay the renderer cannot draw is a caller error, not something to skip."""
    with pytest.raises(TypeError, match="Unsupported overlay type: Overlay"):
        logger.save_image("drift.png", image, [Overlay()])


def test_save_image_rejects_an_unsupported_overlay_among_valid_ones(
    logger: FileImageLogger, image: np.ndarray
) -> None:
    overlays = [RectangleOverlay(0.0, 0.0, 1.0, 1.0), Overlay()]

    with pytest.raises(TypeError):
        logger.save_image("drift.png", image, overlays)


def test_save_image_closes_its_figure_when_an_overlay_is_rejected(
    logger: FileImageLogger, image: np.ndarray
) -> None:
    with pytest.raises(TypeError):
        logger.save_image("drift.png", image, [Overlay()])

    assert plt.get_fignums() == []


def test_second_save_does_not_overwrite_the_first(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image)
    logger.save_image("drift.png", image)

    assert cursor.names() == ["drift.png", "drift_2.png"]


def test_third_save_increments_further(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    for _ in range(3):
        logger.save_image("drift.png", image)

    assert cursor.names() == ["drift.png", "drift_2.png", "drift_3.png"]


def test_collisions_are_counted_across_images_and_plots(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("out.png", image)
    logger.save_plot("out.png", [])

    assert cursor.names() == ["out.png", "out_2.png"]


def test_collisions_are_per_slice_directory(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image)
    cursor.advance_to(1)
    logger.save_image("drift.png", image)

    assert cursor.names(0) == ["drift.png"]
    assert cursor.names(1) == ["drift.png"]


def test_distinct_filenames_do_not_collide(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift.png", image)
    logger.save_image("focus.png", image)

    assert cursor.names() == ["drift.png", "focus.png"]


def test_prefix_is_not_treated_as_a_collision(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift_map.png", image)
    logger.save_image("drift.png", image)

    assert cursor.names() == ["drift.png", "drift_map.png"]


def test_a_different_extension_is_not_a_collision(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    (cursor.dir(0) / "drift.txt").write_text("notes")

    logger.save_image("drift.png", image)

    assert "drift.png" in cursor.names()


def test_a_different_extension_does_not_inflate_the_index(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    (cursor.dir(0) / "drift_9.txt").write_text("notes")

    logger.save_image("drift.png", image)
    logger.save_image("drift.png", image)

    assert "drift_2.png" in cursor.names()


def test_a_directory_with_the_same_stem_is_not_a_collision(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    """Only files are scanned; a subdirectory must not push the filename along."""
    (cursor.dir(0) / "drift").mkdir()

    logger.save_image("drift.png", image)

    assert "drift.png" in cursor.names()


def test_explicitly_numbered_filename_is_honoured(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    """A caller who numbers a filename gets that number, not a renumbering."""
    logger.save_image("drift.png", image)
    logger.save_image("drift_7.png", image)

    assert cursor.names() == ["drift.png", "drift_7.png"]


def test_explicitly_numbered_filename_increments_on_collision(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.save_image("drift_7.png", image)
    logger.save_image("drift_7.png", image)

    assert cursor.names() == ["drift_7.png", "drift_8.png"]


def test_a_free_filename_is_used_even_when_numbered_siblings_exist(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    (cursor.dir(0) / "drift_5.png").write_text("x")

    logger.save_image("drift.png", image)

    assert "drift.png" in cursor.names()


def test_slice_reports_the_current_index(
    logger: FileImageLogger, cursor: SliceCursor
) -> None:
    assert logger.slice == 0

    cursor.advance_to(7)

    assert logger.slice == 7


def test_at_writes_to_the_requested_slice(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.at(5).save_image("out_of_band.png", image)

    assert cursor.names(5) == ["out_of_band.png"]


def test_at_reports_the_requested_slice(logger: FileImageLogger) -> None:
    assert logger.at(5).slice == 5


def test_at_does_not_move_the_original_logger(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.at(5).save_image("elsewhere.png", image)
    logger.save_image("here.png", image)

    assert logger.slice == 0
    assert cursor.names(0) == ["here.png"]


def test_at_view_is_pinned_when_the_run_advances(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    pinned = logger.at(3)

    cursor.advance_to(9)
    pinned.save_image("still_three.png", image)

    assert cursor.names(3) == ["still_three.png"]


def test_next_writes_to_the_following_slice(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.next.save_image("upcoming.png", image)

    assert cursor.names(1) == ["upcoming.png"]


def test_next_is_relative_to_the_current_slice(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    cursor.advance_to(4)

    logger.next.save_image("upcoming.png", image)

    assert cursor.names(5) == ["upcoming.png"]


def test_next_reports_the_following_slice(
    logger: FileImageLogger, cursor: SliceCursor
) -> None:
    cursor.advance_to(2)

    assert logger.next.slice == 3


def test_next_view_is_pinned_at_access_time(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    view = logger.next

    cursor.advance_to(9)
    view.save_image("pinned.png", image)

    assert cursor.names(1) == ["pinned.png"]


def test_next_of_next_advances_twice(
    logger: FileImageLogger, cursor: SliceCursor, image: np.ndarray
) -> None:
    logger.next.next.save_image("two_ahead.png", image)

    assert cursor.names(2) == ["two_ahead.png"]


def test_save_plot_writes_a_valid_png(
    logger: FileImageLogger, cursor: SliceCursor
) -> None:
    logger.save_plot("sharpness.png", [Curve("red", 1.0, None, [1.0, 2.0, 3.0])])

    assert is_png(cursor.dir(0) / "sharpness.png")


def test_save_plot_with_explicit_x_values(
    logger: FileImageLogger, cursor: SliceCursor
) -> None:
    curve = Curve("red", 1.0, [0.0, 1.0, 2.0], [3.0, 4.0, 5.0])

    logger.save_plot("sharpness.png", [curve])

    assert is_png(cursor.dir(0) / "sharpness.png")


def test_save_plot_with_mismatched_x_and_y_lengths_raises(
    logger: FileImageLogger,
) -> None:
    """Matplotlib rejects it; the logger does not validate first."""
    curve = Curve("red", 1.0, [0.0, 1.0], [3.0, 4.0, 5.0])

    with pytest.raises(ValueError):
        logger.save_plot("sharpness.png", [curve])


def test_save_plot_with_vertical_line(
    logger: FileImageLogger, cursor: SliceCursor
) -> None:
    logger.save_plot("sharpness.png", [VerticalLine("black", 1.0, 1.5)])

    assert is_png(cursor.dir(0) / "sharpness.png")


def test_save_plot_with_mixed_elements(
    logger: FileImageLogger, cursor: SliceCursor
) -> None:
    """A sharpness sweep plots the curve plus a marker at the chosen optimum."""
    elements = [
        Curve("red", 1.0, [0.0, 1.0, 2.0], [3.0, 5.0, 4.0]),
        VerticalLine("black", 0.5, 1.0),
    ]

    logger.save_plot("sharpness.png", elements)

    assert is_png(cursor.dir(0) / "sharpness.png")


def test_save_plot_with_no_elements_still_writes_a_file(
    logger: FileImageLogger, cursor: SliceCursor
) -> None:
    logger.save_plot("empty.png", [])

    assert is_png(cursor.dir(0) / "empty.png")


def test_save_plot_accepts_labels(logger: FileImageLogger, cursor: SliceCursor) -> None:
    logger.save_plot(
        "sharpness.png",
        [Curve("red", 1.0, None, [1.0])],
        title="Sharpness",
        xlabel="working distance [nm]",
        ylabel="sharpness",
    )

    assert is_png(cursor.dir(0) / "sharpness.png")


def test_save_plot_follows_the_slice(
    logger: FileImageLogger, cursor: SliceCursor
) -> None:
    logger.save_plot("zero.png", [])
    cursor.advance_to(3)
    logger.save_plot("three.png", [])

    assert cursor.names(0) == ["zero.png"]
    assert cursor.names(3) == ["three.png"]


def test_save_plot_closes_its_figure(logger: FileImageLogger) -> None:
    logger.save_plot("sharpness.png", [Curve("red", 1.0, None, [1.0])])

    assert plt.get_fignums() == []


def test_save_plot_closes_its_figure_on_failure(logger: FileImageLogger) -> None:
    """A failed render must not leak the figure; pyplot holds it forever."""
    curve = Curve("red", 1.0, [0.0, 1.0], [3.0, 4.0, 5.0])

    with pytest.raises(ValueError):
        logger.save_plot("sharpness.png", [curve])

    assert plt.get_fignums() == []
