# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import re
import threading
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, BinaryIO, Self

import matplotlib as mpl
from matplotlib.figure import Figure

from fibsem_maestro.logging.image.plot_element import Curve, PlotElement, VerticalLine
from fibsem_maestro.slice.slice_view import SliceView

mpl.use("Agg")
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle
from numpy.typing import NDArray

from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.image.overlay import (
    HeatmapOverlay,
    Overlay,
    PolylineOverlay,
    RectangleOverlay,
    VerticalLineOverlay,
)

# serialize matplotlib layout and rasterisation across all logger instances
_RENDER_LOCK = threading.Lock()

_DEFAULT_SUFFIX = ".png"


class FileImageLogger(ImageLogger):
    """
    `ImageLogger` that renders and writes PNG files into the slice directory.

    Images and plots are rendered with Matplotlib and written directly into
    the flat slice directory resolved by `view_provider`. If a file with the
    same stem already exists in that directory, a numeric suffix is appended to
    avoid overwriting it.

    Thread-safe: concurrent calls, including calls with identical filenames,
    always produce distinct files.

    Args:
        view_provider: Callable returning the `SliceView` to write to.
    """

    def __init__(self, view_provider: Callable[[], SliceView]) -> None:
        self._view_provider = view_provider

    def save_image(
        self,
        filename: str,
        img: NDArray[Any],
        overlays: Sequence[Overlay] | None = None,
        title: str | None = None,
    ) -> None:
        """
        Render and save a grayscale image as a PNG.

        Args:
            filename: Output filename with extension, relative to the current slice directory.
            img: 2D floating-point array containing the image data.
            overlays: Optional sequence of overlay objects to draw on the
                image. Supported types are `RectangleOverlay`, `PolylineOverlay`,
                `VerticalLineOverlay`, and `HeatmapOverlay`. Unsupported types are silently skipped.
            title: Optional title rendered above the image.

        Raises:
            TypeError: If an overlay's type has no renderer defined.
        """
        directory = self._view_provider().path()

        fig, ax = self._new_figure()
        ax.imshow(img, cmap="gray")

        if overlays:
            self._draw_overlays(ax, overlays)

        if title:
            ax.set_title(title)

        ax.axis("off")

        self._write(fig, directory / filename)

    def save_plot(
        self,
        filename: str,
        elements: Sequence[PlotElement],
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
    ) -> None:
        """
        Render and save a multi-curve plot as a PNG.

        Args:
            filename: Output filename with extension, relative to the current slice directory.
            elements: Sequence of `PlotElement` objects defining the data.
            title: Optional title rendered above the plot.
            xlabel: Optional x-axis label.
            ylabel: Optional y-axis label.
        """
        directory = self._view_provider().path()

        fig, ax = self._new_figure()
        for element in elements:
            match element:
                case Curve():
                    if element.x is None:
                        ax.plot(
                            element.y,
                            color=element.color,
                            linewidth=element.linewidth,
                        )
                    else:
                        ax.plot(
                            element.x,
                            element.y,
                            color=element.color,
                            linewidth=element.linewidth,
                        )
                case VerticalLine():
                    ax.axvline(
                        x=element.x,
                        color=element.color,
                        linewidth=element.linewidth,
                    )

        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

        self._write(fig, directory / filename)

    def at(self, slice_index: int) -> Self:
        """
        Return a view of this logger scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `FileImageLogger` writing to the given slice directory.
        """
        fixed = SliceView(self._view_provider().action_dir, slice_index)
        return type(self)(lambda: fixed)

    @property
    def next(self) -> Self:
        """
        Return a view of this logger scoped to the next slice.

        Returns:
            A `FileImageLogger` writing to the slice after the current one.
        """
        view = self._view_provider()
        fixed = SliceView(view.action_dir, view.slice_index + 1)
        return type(self)(lambda: fixed)

    @property
    def slice(self) -> int:
        return self._view_provider().slice_index

    def _draw_overlays(self, ax: Axes, overlays: Sequence[Overlay]) -> None:
        """
        Apply overlay objects to a Matplotlib axes.

        Args:
            ax: The axes to draw onto.
            overlays: Sequence of overlay definitions.

        Raises:
            TypeError: If an overlay's type has no renderer defined.
        """
        for overlay in overlays:
            match overlay:
                case RectangleOverlay():
                    ax.add_patch(
                        Rectangle(
                            (overlay.x, overlay.y),
                            overlay.width,
                            overlay.height,
                            fill=False,
                            edgecolor=overlay.color,
                            linewidth=overlay.linewidth,
                            alpha=overlay.alpha,
                        )
                    )
                case PolylineOverlay():
                    xs = [p.x for p in overlay.points]
                    ys = [p.y for p in overlay.points]
                    ax.plot(xs, ys, color=overlay.color, linewidth=overlay.linewidth)
                case VerticalLineOverlay():
                    ax.axvline(
                        x=overlay.x,
                        color=overlay.color,
                        linewidth=overlay.linewidth,
                    )
                case HeatmapOverlay():
                    ax.imshow(overlay.data, cmap="hot", alpha=overlay.alpha)
                case _:
                    raise TypeError(
                        f"Unsupported overlay type: {type(overlay).__name__}."
                    )

    @classmethod
    def _write(cls, fig: Figure, path: Path) -> None:
        """
        Lay out and save a figure to a unique path derived from `path`.

        Args:
            fig: The figure to save.
            path: The desired output path; its extension selects the format.
        """
        if not path.suffix:
            # append instead of using `with_suffix` since that could mangle names like `focus_1.5`
            path = path.with_name(path.name + _DEFAULT_SUFFIX)

        with _RENDER_LOCK:
            fig.tight_layout()

        with cls._reserve(path) as fh, _RENDER_LOCK:
            fig.savefig(fh, format=path.suffix.lstrip("."), dpi=100)

    @classmethod
    @contextmanager
    def _reserve(cls, path: Path) -> Iterator[BinaryIO]:
        """
        Atomically claim a unique output path and yield it opened for writing.

        The file is created with exclusive-create semantics (`O_CREAT |
        O_EXCL`), so concurrent callers, whether threads or processes, can
        never be handed the same path. The empty placeholder is visible to
        other callers' directory scans, which therefore pick the next number.
        If writing fails, the placeholder is removed.

        Args:
            path: The desired output path.

        Yields:
            A binary file handle to the claimed path.
        """
        while True:
            candidate = cls._unique_path(path)
            try:
                fh = candidate.open("xb")
            except FileExistsError:
                # lost the race; rescan, which now sees the winner's file
                continue
            break

        try:
            with fh:
                yield fh
        except BaseException:
            candidate.unlink(missing_ok=True)
            raise

    @staticmethod
    def _unique_path(path: Path) -> Path:
        """
        Return the requested path, or a numbered variant if it is taken.

        The requested path is returned unchanged whenever nothing occupies it,
        so a caller-supplied number such as `sweep_3.png` is honoured. On a
        real collision, the trailing `_N` is stripped and the directory is
        scanned for files sharing that stem and extension; the returned path
        carries a number one above the highest found. Directories and files
        with other extensions are ignored, and gaps in the numbering are not
        filled.

        This only *proposes* a candidate and is not safe on its own under
        concurrency; use `_reserve` to claim the path.

        Args:
            path: The desired output path.

        Returns:
            The original path if it is free, otherwise a path of the form `<stem>_N<suffix>`.
        """
        if not path.exists():
            return path

        clean_stem = re.sub(r"_\d+$", "", path.stem)

        nums: list[int] = []
        for p in path.parent.iterdir():
            if not p.is_file() or p.suffix != path.suffix:
                continue
            if p.stem == clean_stem:
                nums.append(1)
            elif p.stem.startswith(clean_stem + "_"):
                rest = p.stem[len(clean_stem) + 1 :]
                if rest.isdigit():
                    nums.append(int(rest))

        if not nums:
            return path

        return path.with_name(f"{clean_stem}_{max(nums) + 1}{path.suffix}")

    @staticmethod
    def _new_figure() -> tuple[Figure, Axes]:
        """
        Create a standalone figure that does not use pyplot's global state.

        The figure is not registered with any figure manager, so it does not need
        explicit closing and is garbage-collected normally. Saving it renders
        through Agg regardless of the active GUI backend.

        Returns:
            The figure and its single axes.
        """
        fig = Figure()
        return fig, fig.subplots()
