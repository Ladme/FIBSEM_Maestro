# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import re
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Self

import matplotlib as mpl
from matplotlib.figure import Figure

from fibsem_maestro.logging.image.plot_element import Curve, PlotElement, VerticalLine
from fibsem_maestro.slice.slice_view import SliceView

mpl.use("Agg")
from matplotlib import pyplot as plt
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


class FileImageLogger(ImageLogger):
    """
    `ImageLogger` that renders and writes PNG files into the slice directory.

    Images and plots are rendered with Matplotlib and written directly into
    the flat slice directory resolved by `view_provider`. If a file with the
    same stem already exists in that directory, a numeric suffix is appended to
    avoid overwriting it.

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
        """
        with self._figure() as (fig, ax):
            ax.imshow(img, cmap="gray")

            if overlays:
                self._draw_overlays(ax, overlays)

            if title:
                ax.set_title(title)

            ax.axis("off")
            fig.tight_layout()

            out_path = self._unique_path(self._view_provider().path() / filename)
            fig.savefig(out_path, dpi=100)

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
        with self._figure() as (fig, ax):
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

            fig.tight_layout()

            out_path = self._unique_path(self._view_provider().path() / filename)
            fig.savefig(out_path, dpi=100)

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

        next_index = self._view_provider().slice_index + 1
        fixed = SliceView(self._view_provider().action_dir, next_index)
        return type(self)(lambda: fixed)

    @property
    def slice(self) -> int:
        return self._view_provider().slice_index

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
    @contextmanager
    def _figure() -> Iterator[tuple[Figure, Axes]]:
        """
        Yield a fresh Matplotlib figure and axes, closing the figure on exit.

        Yields:
            The figure and its axes.
        """
        fig, ax = plt.subplots()
        try:
            yield fig, ax
        finally:
            plt.close(fig)
