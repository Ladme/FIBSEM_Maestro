# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Self

import numpy as np
from numpy.typing import NDArray

from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.image.overlay import Overlay
from fibsem_maestro.logging.image.plot_element import PlotElement


@dataclass
class SavedImage:
    """
    A single image entry captured by `MemoryImageLogger`.

    Attributes:
        slice_index: The slice during which this image was saved.
        filename: The filename supplied by the caller.
        img: A copy of the image array.
        overlays: The overlay objects supplied by the caller, or `None`.
        title: The title supplied by the caller, or `None`.
    """

    slice_index: int
    filename: str
    img: NDArray[Any]
    overlays: list[Overlay] | None
    title: str | None


@dataclass
class SavedPlot:
    """
    A single plot entry captured by `MemoryImageLogger`.

    Attributes:
        slice_index: The slice during which this plot was saved.
        filename: The filename supplied by the caller.
        elements: The plot elements supplied by the caller.
        title: The title supplied by the caller, or `None`.
        xlabel: The x-axis label supplied by the caller, or `None`.
        ylabel: The y-axis label supplied by the caller, or `None`.
    """

    slice_index: int
    filename: str
    elements: list[PlotElement]
    title: str | None
    xlabel: str | None
    ylabel: str | None


class MemoryImageLogger(ImageLogger):
    """
    `ImageLogger` that stores images and plots in memory.

    All instances sharing the same record stores (created via `at()` or
    `next`) write into those shared stores, keyed by slice index.

    Args:
        slice_provider: Callable returning the current slice index.
        _images: Shared image record store. When `None` a fresh dict is
            created, making this instance the root of a new record group.
        _plots: Shared plot record store. When `None` a fresh dict is
            created, making this instance the root of a new record group.
    """

    def __init__(
        self,
        slice_provider: Callable[[], int],
        *,
        _images: dict[int, list[SavedImage]] | None = None,
        _plots: dict[int, list[SavedPlot]] | None = None,
    ) -> None:
        self._slice_provider = slice_provider
        self._images: dict[int, list[SavedImage]] = (
            defaultdict(list) if _images is None else _images
        )
        self._plots: dict[int, list[SavedPlot]] = (
            defaultdict(list) if _plots is None else _plots
        )

    @property
    def images(self) -> dict[int, list[SavedImage]]:
        """
        All saved images grouped by slice index.

        Returns:
            A dict mapping slice index to the list of images saved in that
            slice, across this logger and any navigated views.
        """
        return self._images

    @property
    def plots(self) -> dict[int, list[SavedPlot]]:
        """
        All saved plots grouped by slice index.

        Returns:
            A dict mapping slice index to the list of plots saved in that
            slice, across this logger and any navigated views.
        """
        return self._plots

    def save_image(
        self,
        filename: str,
        img: NDArray[Any],
        overlays: Sequence[Overlay] | None = None,
        title: str | None = None,
    ) -> None:
        idx = self._slice_provider()
        self._images[idx].append(
            SavedImage(
                slice_index=idx,
                filename=filename,
                img=np.array(img, copy=True),
                overlays=list(overlays) if overlays is not None else None,
                title=title,
            )
        )

    def save_plot(
        self,
        filename: str,
        elements: Sequence[PlotElement],
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
    ) -> None:
        idx = self._slice_provider()
        self._plots[idx].append(
            SavedPlot(
                slice_index=idx,
                filename=filename,
                elements=list(elements),
                title=title,
                xlabel=xlabel,
                ylabel=ylabel,
            )
        )

    def at(self, slice_index: int) -> Self:
        """
        Return a view of this logger scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `MemoryImageLogger` sharing the same record stores but writing
            to the given slice index.
        """
        return type(self)(
            lambda: slice_index,
            _images=self._images,
            _plots=self._plots,
        )

    @property
    def next(self) -> Self:
        """
        Return a view of this logger scoped to the next slice.

        Returns:
            A `MemoryImageLogger` writing to the slice after the current one.
        """
        next_index = self._slice_provider() + 1
        return type(self)(
            lambda: next_index,
            _images=self._images,
            _plots=self._plots,
        )

    @property
    def slice(self) -> int:
        return self._slice_provider()
