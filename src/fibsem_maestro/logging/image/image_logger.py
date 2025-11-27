# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from collections.abc import Sequence

from fibsem_maestro.core.image import Image
from fibsem_maestro.logging.image.curve import Curve
from fibsem_maestro.logging.image.overlay import Overlay


class ImageLogger(ABC):
    """
    Interface for image and plot logging.

    Implementations of this interface provide mechanisms for saving images
    with optional overlays and saving plot figures composed of one or more curves.
    """

    @abstractmethod
    def save_image(
        self,
        filename: str,
        img: Image,
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
        pass

    @abstractmethod
    def save_plot(
        self,
        filename: str,
        curves: Sequence[Curve],
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
    ) -> None:
        """
        Save a plot composed of one or more curves.

        Args:
            filename: Output filename, relative to the logger's output directory.
            curves: A sequence of Curve objects defining the data to plot.
            title: Optional plot title.
            xlabel: Optional label for the x-axis.
            ylabel: Optional label for the y-axis.
        """
        pass
