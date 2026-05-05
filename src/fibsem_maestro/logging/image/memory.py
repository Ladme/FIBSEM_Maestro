# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray

from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.image.overlay import Overlay
from fibsem_maestro.logging.image.plot_element import PlotElement


class MemoryImageLogger(ImageLogger):
    """ImageLogger that stores images in memory for testing purposes."""

    def __init__(self) -> None:
        self.saved_images: list[dict[str, Any]] = []
        self.saved_plots: list[dict[str, Any]] = []

    def save_image(
        self,
        filename: str,
        img: NDArray[np.floating],
        overlays: Sequence[Overlay] | None = None,
        title: str | None = None,
    ) -> None:
        self.saved_images.append(
            {
                "filename": filename,
                "img": np.array(img, copy=True),
                "overlays": list(overlays) if overlays is not None else None,
                "title": title,
            }
        )

    def save_plot(
        self,
        filename: str,
        elements: Sequence[PlotElement],
        title: str | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
    ) -> None:
        self.saved_plots.append(
            {
                "filename": filename,
                "elements": list(elements),
                "title": title,
                "xlabel": xlabel,
                "ylabel": ylabel,
            }
        )
