# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

import math

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsPixmapItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

class MipmapPixmapItem(QGraphicsPixmapItem):
    """
    A pixmap item that low-pass filters before minifying.

    Args:
        pixmap: The full-resolution image.
        min_level_size: Pyramid generation stops below this size in either dimension.
        parent: Parent graphics item.
    """

    def __init__(
            self,
            pixmap: QPixmap,
            min_level_size: int = 64,
            parent: QGraphicsItem | None = None,
    ) -> None:
        super().__init__(pixmap, parent)
        # QGraphicsPixmapItem defaults to FastTransformation, and the base
        # level is painted by the superclass, so set the mode explicitly
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self._min_level_size = min_level_size
        self._levels: list[QPixmap] = [pixmap]
        self._build_pyramid()

    def _build_pyramid(self) -> None:
        """
        Generate half-size levels by exact 2x2 averaging.

        A 2:1 reduction with `SmoothTransformation` reads every source pixel
        exactly once, so chaining halvings gives a box-filtered pyramid. Total
        cost is about a third more memory than the base level.
        """
        current = self._levels[0]
        while (
                current.width() // 2 >= self._min_level_size
                and current.height() // 2 >= self._min_level_size
        ):
            current = current.scaled(
                current.width() // 2,
                current.height() // 2,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._levels.append(current)

    def set_image(self, pixmap: QPixmap) -> None:
        """
        Replace the image and rebuild the pyramid.

        Args:
            pixmap: The new full-resolution image.
        """
        self.setPixmap(pixmap)
        self._levels = [pixmap]
        self._build_pyramid()
        self.update()

    def _level_for_scale(self, scale: float) -> QPixmap:
        """
        Return the smallest level still at or above the on-screen resolution.

        Args:
            scale: On-screen pixels per image pixel.

        Returns:
            The pyramid level to paint.
        """
        if scale >= 1.0 or scale <= 0.0:
            return self._levels[0]

        index = math.floor(math.log2(1.0 / scale))
        return self._levels[max(0, min(index, len(self._levels) - 1))]

    def paint(
            self,
            painter: QPainter,
            option: QStyleOptionGraphicsItem,
            widget: QWidget | None = None,
    ) -> None:
        """Paint the appropriate pyramid level over the item's full rectangle."""
        scale = option.levelOfDetailFromTransform(painter.worldTransform())
        level = self._level_for_scale(scale)

        if level is self._levels[0]:
            super().paint(painter, option, widget)
            return

        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        pixmap = self.pixmap()
        painter.drawPixmap(
            QRectF(0.0, 0.0, float(pixmap.width()), float(pixmap.height())),
            level,
            QRectF(0.0, 0.0, float(level.width()), float(level.height())),
        )