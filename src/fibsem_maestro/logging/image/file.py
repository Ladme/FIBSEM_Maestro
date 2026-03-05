# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Sequence

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle
from numpy.typing import NDArray

from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.logging.image.curve import Curve
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
    ImageLogger that renders and writes PNG files into slice-aware directories.

    Images and plots are rendered with Matplotlib and written to the `images`
    subdirectory of the current slice, as resolved by the provided `SliceContext`.

    Args:
        ctx: Slice context used to resolve the active image output directory.
    """

    def __init__(self, ctx: SliceContext):
        """
        Args:
            ctx: Slice context used to resolve the active image output directory.
        """
        self._ctx = ctx

    def save_image(
        self,
        filename: str,
        img: NDArray[np.floating],
        overlays: Sequence[Overlay] | None = None,
        title: str | None = None,
    ) -> None:
        """
        Render and save a grayscale image as a PNG, optionally annotated with overlays.

        The file is written to the current slice's image directory as
        `{filename}.png`. Supported overlay types are `RectangleOverlay`,
        `PolylineOverlay`, `VerticalLineOverlay`, and `HeatmapOverlay`.

        Args:
            filename: Output filename without extension, relative to the current
                slice's image directory.
            img: 2-D floating-point array containing the image data.
            overlays: Optional sequence of overlay objects to draw on top of the
                image. Unsupported overlay types are silently skipped.
            title: Optional title rendered above the image.
        """
        fig, ax = plt.subplots()
        ax.imshow(img, cmap="gray")

        if overlays:
            self._set_overlays(ax, overlays)

        if title:
            ax.set_title(title)

        ax.axis("off")
        fig.tight_layout()

        out_path = self._ctx.images() / f"{filename}.png"
        fig.savefig(out_path, dpi=100)
        plt.close(fig)

    def _set_overlays(self, ax: Axes, overlays: Sequence[Overlay]) -> None:
        """
        Apply overlay objects to the Matplotlib axes.

        Args:
            ax: Matplotlib axes object where overlays will be drawn.
            overlays: A sequence of overlay definitions.
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
                    x=overlay.x, color=overlay.color, linewidth=overlay.linewidth
                )

            elif isinstance(overlay, HeatmapOverlay):
                ax.imshow(overlay.data, cmap="hot", alpha=overlay.alpha)

    def save_plot(
        self,
        filename: str,
        curves: Sequence[Curve],
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
    ) -> None:
        """
        Render and save a multi-curve plot as a PNG.

        Args:
            filename: Output filename without extension, relative to the current
                slice's image directory.
            curves: Sequence of `Curve` objects to plot.
            title: Optional title rendered above the plot.
            xlabel: Optional x-axis label.
            ylabel: Optional y-axis label.
        """
        fig, ax = plt.subplots()

        for curve in curves:
            if curve.x is None:
                ax.plot(curve.y, color=curve.color, linewidth=curve.linewidth)
            else:
                ax.plot(curve.x, curve.y, color=curve.color, linewidth=curve.linewidth)

        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

        fig.tight_layout()

        out_path = self._ctx.images() / f"{filename}.png"
        fig.savefig(out_path, dpi=100)
        plt.close(fig)
