# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Self

from numpy.typing import NDArray

from fibsem_maestro.logging.image.overlay import Overlay
from fibsem_maestro.logging.image.plot_element import PlotElement


class ImageLogger(ABC):
    """
    Abstract interface for image and plot logging.

    Implementations provide mechanisms for saving diagnostic images with
    optional geometric overlays and for saving plots composed of one or
    more curves.
    """

    @abstractmethod
    def save_image(
        self,
        filename: str,
        img: NDArray[Any],
        overlays: Sequence[Overlay] | None = None,
        title: str | None = None,
    ) -> None:
        """
        Save an image with optional geometric overlays.

        Args:
            filename: Output filename, relative to the logger's output directory.
            img: 2D array-like image data to render.
            overlays: Optional sequence of overlay objects describing
                geometric annotations to draw on top of the image.
            title: Optional title text to render above the image.
        """

    @abstractmethod
    def save_plot(
        self,
        filename: str,
        elements: Sequence[PlotElement],
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
    ) -> None:
        """
        Save a plot composed of one or more curves.

        Args:
            filename: Output filename, relative to the logger's output directory.
            elements: A sequence of PlotElement objects defining the data to plot.
            title: Optional plot title.
            xlabel: Optional label for the x-axis.
            ylabel: Optional label for the y-axis.
        """

    @abstractmethod
    def at(self, slice_index: int) -> Self:
        """
        Return a view of this logger scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            An `ImageLogger` of the same concrete type writing to the given
            slice.
        """

    @property
    @abstractmethod
    def next(self) -> Self:
        """
        Return a view of this logger scoped to the next slice.

        Returns:
            An `ImageLogger` of the same concrete type writing to the slice
            after the current one.
        """

    @property
    @abstractmethod
    def slice(self) -> int:
        """
        The slice index this logger is currently writing to.

        Returns:
            The current slice index.
        """
