# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Sequence
from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle
from numpy.typing import NDArray

from fibsem_maestro.logging.context import LogContext
from fibsem_maestro.logging.image.curve import Curve
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.image.overlay import (
    HeatmapOverlay,
    Overlay,
    PolylineOverlay,
    RectangleOverlay,
    VerticalLineOverlay,
)


class SliceAwareImageLogger(ImageLogger):
    """
    Image logger that saves figures into slice-aware directories.

    This logger uses a `LogContext` to determine the correct output
    directory based on the currently active slice. Images and plots
    are rendered using Matplotlib and written to disk with overlays,
    curves, or annotations applied as required.
    """

    def __init__(self, ctx: LogContext):
        """Initialize a slice-aware image logger.

        Args:
            ctx: The logging context providing directory paths.
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
        Save an image with optional overlays.

        The image is displayed using Matplotlib and saved into the
        slice directory determined by the `LogContext`. Overlays
        such as rectangles, polylines, heatmaps, or vertical lines
        may be drawn on top of the image.

        Args:
            filename: Base filename (without extension) for the saved image.
            img: 2D array-like object representing the image to be saved.
            overlays: Optional list of overlay objects to render on top
                of the image. If omitted, the raw image is saved.
            title: Optional title to display at the top of the figure.
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
        Save a plot containing one or more curves.

        Args:
            filename: Base filename (without extension) for the saved plot.
            curves: A sequence of `Curve` objects defining data series to be plotted.
            title: Optional title for the plot.
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
