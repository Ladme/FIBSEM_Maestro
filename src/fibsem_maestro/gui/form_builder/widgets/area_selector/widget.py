# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.gui.form_builder.widgets.area_selector._rectangle import (
    ResizableRect,
)
from fibsem_maestro.gui.form_builder.widgets.area_selector._viewer import _AreaViewer
from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper
from fibsem_maestro.microscope.microscope import Microscope


class AreaSelectWidget(QWidget, WidgetWrapper):
    """
    Accordion-style area selector widget.

    Collapsed state: shows a thumbnail of the last acquired image (or a
    placeholder if none), a region count, and an expand button.

    Expanded state: shows the full interactive viewer with acquire, clear,
    fit-view buttons and a status bar. Clicking the header collapses it back.

    Args:
        microscope: Microscope instance.
        max_areas: Maximum number of areas. None means unlimited.
        default: Pre-populated list of RelativeArea areas.
        parent: Parent widget.
    """

    _THUMBNAIL_HEIGHT = 100
    _EXPANDED_HEIGHT = 600
    _MINIMUM_WIDTH = 800

    def __init__(
        self,
        microscope: Microscope | None,
        max_areas: int | None = None,
        default: list[RelativeArea] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        WidgetWrapper.__init__(self)

        self._microscope = microscope
        self._max_areas = max_areas
        self._image_size: tuple[int, int] | None = None
        self._last_pixmap: QPixmap | None = None
        self._pending_regions: list[RelativeArea] = default or []
        self._expanded = False

        self.setMinimumWidth(self._MINIMUM_WIDTH)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # header row (always visible)
        header = QWidget()
        header.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 4)
        header_layout.addStretch()

        self._load_btn = QPushButton("Load")
        self._load_btn.setFixedWidth(70)
        self._load_btn.clicked.connect(self._load_image)
        header_layout.addWidget(self._load_btn)

        self._toggle_btn = QPushButton("▼ Expand")
        self._toggle_btn.setFixedWidth(80)
        self._toggle_btn.clicked.connect(self._toggle)
        header_layout.addWidget(self._toggle_btn)

        outer.addWidget(header)

        # thumbnail (used when collapsed)
        self._thumbnail_label = QLabel()
        self._thumbnail_label.setFixedHeight(self._THUMBNAIL_HEIGHT)
        self._thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail_label.setStyleSheet(
            "background: #1a1a1a; border: 0.5px solid #444; border-radius: 4px;"
        )
        self._thumbnail_label.setText("No image")
        self._thumbnail_label.mousePressEvent = lambda _: self._toggle()  # type: ignore
        self._thumbnail_label.setCursor(Qt.CursorShape.PointingHandCursor)
        outer.addWidget(self._thumbnail_label)

        # expanded viewer (initially hidden)
        self._viewer_container = QWidget()
        self._viewer_container.hide()
        viewer_layout = QVBoxLayout(self._viewer_container)
        viewer_layout.setContentsMargins(0, 4, 0, 0)
        viewer_layout.setSpacing(4)

        # toolbar
        status_box = QHBoxLayout()
        status_box.addStretch()
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 11px;")
        status_box.addWidget(self._status_label)
        viewer_layout.addLayout(status_box)

        # the actual viewer
        self._scene = QGraphicsScene()
        self._scene.changed.connect(self._on_scene_changed)
        self._viewer = _AreaViewer(
            self._scene, self._status_label.setText, self._max_areas
        )
        self._viewer.setFixedHeight(self._EXPANDED_HEIGHT)
        self._viewer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        viewer_layout.addWidget(self._viewer)
        outer.addWidget(self._viewer_container)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._thumbnail_label.setVisible(not self._expanded)
        self._viewer_container.setVisible(self._expanded)
        self._toggle_btn.setText("▲ Collapse" if self._expanded else "▼ Expand")

    def _load_image(self) -> None:
        self._load_btn.setEnabled(False)
        self._status_label.setText("Loading image...")
        try:
            if self._microscope is None:
                raise ValueError("FIBSEM Maestro is not connected to a microscope.")
            image = self._microscope.beam.get_image()
            self.convert_image(image)
        except Exception as e:
            self._status_label.setText(f"Acquisition failed: {e}")
        finally:
            self._load_btn.setEnabled(True)

    def convert_image(self, image: Image) -> None:
        """Convert and display an image. Preserves any existing rectangles."""
        arr = image.to_8bit()
        h, w = arr.shape[:2]
        self._image_size = (w, h)

        if arr.ndim == 2:
            q_image = QImage(arr.data.tobytes(), w, h, QImage.Format.Format_Grayscale8)
        else:
            q_image = QImage(arr.data.tobytes(), w, h, QImage.Format.Format_RGB888)

        self._last_pixmap = QPixmap.fromImage(q_image)

        # update scene - remove old pixmap, keep rectangles
        for item in list(self._scene.items()):
            if not isinstance(item, (ResizableRect, QGraphicsEllipseItem)):
                self._scene.removeItem(item)

        pixmap_item = self._scene.addPixmap(self._last_pixmap)
        pixmap_item.setZValue(-1)
        self._scene.setSceneRect(QRectF(0, 0, w, h))
        self._viewer.reset_zoom()

        # update thumbnail
        self._update_thumbnail()

        # apply pending regions
        for area in self._pending_regions:
            self._add_relative_area(area)
        self._pending_regions = []

        self._viewer.set_image_loaded()
        self._status_label.setText(f"Image: {w}×{h} px")

    def _on_scene_changed(self, _) -> None:
        self._update_thumbnail()
        self._notify_changed()

    def _update_thumbnail(self) -> None:
        if self._last_pixmap is None:
            return

        # render the full scene into a pixmap at thumbnail scale
        scene_rect = self._scene.sceneRect()
        aspect = (
            scene_rect.width() / scene_rect.height() if scene_rect.height() > 0 else 1.0
        )
        thumb_w = int(self._THUMBNAIL_HEIGHT * aspect)
        thumb_h = self._THUMBNAIL_HEIGHT

        thumbnail = QPixmap(thumb_w, thumb_h)
        thumbnail.fill(Qt.GlobalColor.black)

        painter = QPainter(thumbnail)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._scene.render(painter, QRectF(0, 0, thumb_w, thumb_h), scene_rect)
        painter.end()

        self._thumbnail_label.setPixmap(thumbnail)

    def _add_relative_area(self, area: RelativeArea) -> None:
        if self._image_size is None:
            return
        w, h = self._image_size
        rect = QRectF(
            area.origin.x * w,
            area.origin.y * h,
            area.width * w,
            area.height * h,
        )
        self._scene.addItem(ResizableRect(rect))
        self._update_thumbnail()

    def get_value(self) -> list[RelativeArea]:
        if self._image_size is None:
            return []
        w, h = self._image_size
        result = []
        for item in self._scene.items():
            if isinstance(item, ResizableRect):
                sr = item.scene_rect()
                result.append(
                    RelativeArea(
                        origin=RelativePoint(
                            x=max(0.0, min(1.0, sr.x() / w)),
                            y=max(0.0, min(1.0, sr.y() / h)),
                        ),
                        width=min(1.0, sr.width() / w),
                        height=min(1.0, sr.height() / h),
                    )
                )
        return result

    def _clear_rects(self) -> None:
        for item in list(self._scene.items()):
            if isinstance(item, ResizableRect):
                self._scene.removeItem(item)

        self._update_thumbnail()

    def set_value(self, value: Any) -> None:
        self._clear_rects()
        regions = value or []
        if self._image_size is None:
            self._pending_regions = regions
        else:
            for area in regions:
                self._add_relative_area(area)

    def set_read_only(self, read_only: bool) -> None:
        self._load_btn.setEnabled(not read_only)
        self._toggle_btn.setEnabled(not read_only)
        self._viewer.set_read_only(read_only)
