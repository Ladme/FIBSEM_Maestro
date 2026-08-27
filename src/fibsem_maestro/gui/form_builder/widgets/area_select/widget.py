# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


import numpy as np
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
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
from fibsem_maestro.gui.form_builder.widgets.area_select._rectangle import (
    ResizableRect,
)
from fibsem_maestro.gui.form_builder.widgets.area_select._viewer import AreaViewer
from fibsem_maestro.gui.form_builder.widgets.area_select.overlay import (
    OverlayData,
    build_decoration,
)
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.form_utils import AreaOverlay


class AreaSelectWidget(QWidget, BaseWidget[list[RelativeArea]]):
    """
    Accordion-style selector for rectangular acquisition areas.

    Collapsed, it shows a thumbnail with a region overlay.
    Expanded, it shows an interactive viewer for drawing, moving, resizing,
    and deleting areas over the last acquired image.

    Args:
        microscope: Microscope instance used to acquire images, or None.
        max_areas: Maximum number of areas, or None for unlimited.
        default: Pre-populated areas, applied once an image is available.
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
        overlay: AreaOverlay | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        BaseWidget.__init__(self)

        self._microscope = microscope
        self._max_areas = max_areas
        self._image_size: tuple[int, int] | None = None
        self._last_pixmap: QPixmap | None = None
        self._pending_regions: list[RelativeArea] = default or []
        self._expanded = False

        self._overlay = overlay
        self._overlay_data: OverlayData | None = None
        self._pixel_size: float | None = None

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

        # Temporary diagnostics button
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<
        self._diag_btn = QPushButton("Capture")
        self._diag_btn.setFixedWidth(80)
        self._diag_btn.setToolTip("Save a diagnostic bundle for the frame on screen")
        self._diag_btn.clicked.connect(self._capture_diagnostics)
        header_layout.addWidget(self._diag_btn)
        # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>

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

        status_box = QHBoxLayout()
        status_box.addStretch()
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 11px;")
        status_box.addWidget(self._status_label)
        viewer_layout.addLayout(status_box)

        self._scene = QGraphicsScene()
        # scene.changed drives ONLY the thumbnail
        # committing changes is done via the viewer's edit-finished callback,
        # so a drag does not spam writes
        self._scene.changed.connect(self._on_scene_changed)
        self._viewer = AreaViewer(
            self._scene,
            self._status_label.setText,
            self._max_areas,
            on_edit_finished=self._handle_edit_finished,
        )
        self._viewer.setFixedHeight(self._EXPANDED_HEIGHT)
        self._viewer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        viewer_layout.addWidget(self._viewer)
        outer.addWidget(self._viewer_container)

    def _toggle(self) -> None:
        """Toggle between the collapsed thumbnail and the expanded viewer."""
        self._expanded = not self._expanded
        self._thumbnail_label.setVisible(not self._expanded)
        self._viewer_container.setVisible(self._expanded)
        self._toggle_btn.setText("▲ Collapse" if self._expanded else "▼ Expand")

        if not self._expanded:
            self._update_thumbnail()

    def _load_image(self) -> None:
        """Acquire an image from the microscope and display it."""
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
        """
        Display an image, preserving existing areas and realizing pending ones.

        Args:
            image: The image to display beneath the area overlay.
        """
        arr = np.ascontiguousarray(image.to_8bit())
        h, w = arr.shape[:2]
        self._image_size = (w, h)
        self._pixel_size = image.pixel_size

        if arr.ndim == 2:
            q_image = QImage(
                arr.tobytes(), w, h, arr.strides[0], QImage.Format.Format_Grayscale8
            ).copy()
        else:
            q_image = QImage(
                arr.tobytes(), w, h, arr.strides[0], QImage.Format.Format_RGB888
            ).copy()

        self._last_pixmap = QPixmap.fromImage(q_image)

        # replace the background pixmap, keep the area rectangles and all their children
        for item in list(self._scene.items()):
            if item.parentItem() is None and not isinstance(item, ResizableRect):
                self._scene.removeItem(item)

        pixmap_item = self._scene.addPixmap(self._last_pixmap)
        # set smooth transformation to avoid visual artifacts in compressed images
        pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        pixmap_item.setZValue(-1)
        self._scene.setSceneRect(QRectF(0, 0, w, h))
        self._viewer.reset_zoom()

        self._update_thumbnail()

        # realize any regions deferred while no image was available
        for area in self._pending_regions:
            self._add_relative_area(area)
        self._pending_regions = []

        self._refresh_decorations()
        self._viewer.set_image_loaded()
        self._status_label.setText(f"Image: {w}×{h} px")

        # probably not strictly necessary
        self._emit()

    def _on_scene_changed(self, _) -> None:
        """Refresh the thumbnail on any scene change."""
        if not self._expanded:
            self._update_thumbnail()

    def _update_thumbnail(self) -> None:
        """Render the current scene into the collapsed thumbnail."""
        if self._last_pixmap is None:
            return

        scene_rect = self._scene.sceneRect()
        aspect = (
            scene_rect.width() / scene_rect.height() if scene_rect.height() > 0 else 1.0
        )
        thumb_w = int(self._THUMBNAIL_HEIGHT * aspect)
        thumb_h = self._THUMBNAIL_HEIGHT

        # render at a higher resolution, then downscale with a smoothing filter
        supersample = 3
        hi = QPixmap(thumb_w * supersample, thumb_h * supersample)
        hi.fill(Qt.GlobalColor.black)

        rects = [it for it in self._scene.items() if isinstance(it, ResizableRect)]
        for r in rects:
            r.set_handles_visible(False)
        try:
            painter = QPainter(hi)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            self._scene.render(
                painter, QRectF(0, 0, hi.width(), hi.height()), scene_rect
            )
            painter.end()
        finally:
            for r in rects:
                r.restore_handles()

        thumbnail = hi.scaled(
            thumb_w,
            thumb_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._thumbnail_label.setPixmap(thumbnail)

    def _add_relative_area(self, area: RelativeArea) -> None:
        """
        Add one relative area to the scene as an interactive rectangle.

        Args:
            area: The area to add, in image-relative fractions.
        """
        if self._image_size is None:
            return
        w, h = self._image_size
        rect = QRectF(
            area.origin.x * w,
            area.origin.y * h,
            area.width * w,
            area.height * h,
        )
        self._scene.addItem(
            ResizableRect(rect, on_edit_finished=self._handle_edit_finished)
        )
        self._update_thumbnail()

    def _clear_rects(self) -> None:
        """Remove all area rectangles from the scene."""
        for item in list(self._scene.items()):
            if isinstance(item, ResizableRect):
                self._scene.removeItem(item)
        self._update_thumbnail()

    def _handle_edit_finished(self) -> None:
        """Decorate any newly created areas, then emit the change."""
        self._refresh_decorations()
        self._emit()

    def _refresh_decorations(self) -> None:
        """Rebuild every rectangle's decoration from the current overlay state."""
        if self._overlay_data is None:
            return

        for item in self._scene.items():
            if isinstance(item, ResizableRect):
                item.apply_decoration(
                    build_decoration(
                        self._overlay, self._overlay_data, self._pixel_size
                    )
                )
        self._update_thumbnail()

    def set_overlay_data(self, data: OverlayData) -> None:
        """
        Update the runtime values feeding the overlay and redraw it live.

        Args:
            data: The overlay values (e.g. margin in nm, arrow direction).
        """
        self._overlay_data = data
        self._refresh_decorations()

    def get_value(self) -> list[RelativeArea]:
        """
        Return the current areas as image-relative fractions.

        Before an image is loaded, returns the pending regions unchanged.
        Coordinates are clamped to the unit square.

        Returns:
            The areas currently defined, in scene draw order.
        """
        if self._image_size is None:
            return self._pending_regions
        w, h = self._image_size
        result: list[RelativeArea] = []

        # reversed so reloaded workflows keep the original ordering
        for item in reversed(list(self._scene.items())):
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

    def set_value(self, value: list[RelativeArea]) -> None:
        """
        Replace the current areas (no change emitted).

        If no image is loaded yet, the areas are stored as pending and realized
        on the next `convert_image`.

        Args:
            value: The areas to display, or empty list to clear.
        """
        self._clear_rects()
        regions = value or []
        if self._image_size is None:
            self._pending_regions = regions
        else:
            for area in regions:
                self._add_relative_area(area)
            self._refresh_decorations()

    def set_read_only(self, read_only: bool) -> None:
        """
        Freeze the areas while leaving navigation and collapse available.

        In read-only mode the user can still expand/collapse, zoom, and pan, but
        cannot load a new image, draw, delete, move, or resize areas. Resize
        handles are hidden, since editing is disabled.

        Args:
            read_only: True to freeze area editing and image loading.
        """
        self._load_btn.setEnabled(not read_only)
        # toggle stays enabled: collapse/expand is navigation, not editing
        self._viewer.set_read_only(read_only)
        for item in self._scene.items():
            if isinstance(item, ResizableRect):
                item.set_read_only(read_only)

    # Temporary
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<
    def _capture_diagnostics(self) -> None:
        """Write a diagnostic bundle for the frame currently on screen."""
        if self._microscope is None or self._last_pixmap is None:
            self._status_label.setText("Nothing to capture: no image loaded.")
            return

        self._diag_btn.setEnabled(False)
        self._diag_btn.setText("Saving...")
        QApplication.processEvents()
        try:
            from fibsem_maestro.diagnostics import capture_diagnostics

            folder = capture_diagnostics(self._microscope._control, self)  # ty:ignore[invalid-argument-type]
            message = f"Diagnostics saved to {folder}"
        except Exception as e:
            message = f"Diagnostic capture failed: {e}"
        finally:
            self._diag_btn.setText("Capture")
            self._diag_btn.setEnabled(True)

        self._status_label.setText(message)

    # >>>>>>>>>>>>>>>>>>>>>>>>>>>>>
