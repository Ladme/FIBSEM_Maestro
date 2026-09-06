# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, Self

import matplotlib as mpl

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
        fig, ax = plt.subplots()
        ax.imshow(img, cmap="gray")

        if overlays:
            self._draw_overlays(ax, overlays)

        if title:
            ax.set_title(title)

        ax.axis("off")
        fig.tight_layout()

        out_path = self._unique_path(self._view_provider().path() / filename)
        fig.savefig(out_path, dpi=100)
        plt.close(fig)

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
        fig, ax = plt.subplots()

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
        plt.close(fig)

    def _draw_overlays(self, ax: Axes, overlays: Sequence[Overlay]) -> None:
        """
        Apply overlay objects to a Matplotlib axes.

        Args:
            ax: The axes to draw onto.
            overlays: Sequence of overlay definitions. Unsupported types are silently skipped.
        """
        for overlay in overlays:
            if isinstance(overlay, RectangleOverlay):
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
            elif isinstance(overlay, PolylineOverlay):
                xs = [p.x for p in overlay.points]
                ys = [p.y for p in overlay.points]
                ax.plot(xs, ys, color=overlay.color, linewidth=overlay.linewidth)
            elif isinstance(overlay, VerticalLineOverlay):
                ax.axvline(
                    x=overlay.x,
                    color=overlay.color,
                    linewidth=overlay.linewidth,
                )
            elif isinstance(overlay, HeatmapOverlay):
                ax.imshow(overlay.data, cmap="hot", alpha=overlay.alpha)

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
        Return a unique path by appending or incrementing a numeric suffix.

        Scans the parent directory for files sharing the same stem, regardless
        of extension, and returns a path with a numeric suffix one above the
        current maximum. If no conflicting files exist the original path is
        returned unchanged.

        Args:
            path: The desired output path.

        Returns:
            The original path if no conflict exists, otherwise a path of the
            form `<stem>_N<suffix>` where `N` is one greater than the
            highest conflicting index found.
        """
        clean_stem = re.sub(r"_\d+$", "", path.stem)

        nums: list[int] = []
        for p in path.parent.iterdir():
            if p.stem == clean_stem:
                nums.append(1)
            elif p.stem.startswith(clean_stem + "_"):
                rest = p.stem[len(clean_stem) + 1 :]
                if rest.isdigit():
                    nums.append(int(rest))

        if not nums:
            return path

        return path.with_name(f"{clean_stem}_{max(nums) + 1}{path.suffix}")
