# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Self

from numpy.typing import NDArray

from fibsem_maestro.logging.image.overlay import Overlay
from fibsem_maestro.logging.image.plot import Plot


class ImageLogger(ABC):
    """
    Abstract interface for image and plot logging.

    Implementations provide mechanisms for saving diagnostic images with
    optional geometric overlays and for saving plots composed of one or
    more panels.
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
    def save_plot(self, filename: str, plot: Plot) -> None:
        """
        Save a plot of one or more panels.

        Args:
            filename: Output filename, relative to the logger's output directory.
            plot: The plot to save.
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
