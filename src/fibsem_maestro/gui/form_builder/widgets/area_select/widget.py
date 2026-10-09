# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from collections.abc import Callable, Sequence

import numpy as np
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsScene,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.gui.form_builder.issues import FieldIssue, Severity
from fibsem_maestro.gui.form_builder.widgets.area_select._mipmap import (
    MipmapPixmapItem,
)
from fibsem_maestro.gui.form_builder.widgets.area_select._rectangle import (
    ResizableRect,
)
from fibsem_maestro.gui.form_builder.widgets.area_select._viewer import AreaViewer
from fibsem_maestro.gui.form_builder.widgets.area_select.overlay import (
    AreaDecoration,
    OverlayData,
    build_decorations,
    overlay_problems,
)
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.form_utils import AreaOverlay

_OVERLAY_ISSUE = "overlay"
"""Source key of the warning this widget reports when an overlay cannot be drawn."""


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
        beam_provider: Called just before each acquisition to decide which beam
            to image with. Returning None leaves the active beam untouched.
        parent: Parent widget.
    """

    _THUMBNAIL_HEIGHT = 100
    _EXPANDED_HEIGHT = 600
    _MINIMUM_WIDTH = 800

    def __init__(
        self,
        microscope: Microscope | None,
        txt_log: TextLogger | None,
        max_areas: int | None = None,
        default: list[RelativeArea] | None = None,
        beam_provider: Callable[[], BeamType | None] | None = None,
        offset_provider: Callable[[], float | None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        BaseWidget.__init__(self)

        self._microscope = microscope
        self._txt_log = txt_log
        self._max_areas = max_areas
        self._image_size: tuple[int, int] | None = None
        self._last_pixmap: QPixmap | None = None
        self._pending_regions: list[RelativeArea] = default or []
        self._expanded = False
        self._read_only = False
        # the workflow uses the microscope while it runs, also in danger mode
        self._acquisition_allowed = True

        self._overlays: list[tuple[AreaOverlay, OverlayData]] = []
        self._pixel_size: float | None = None
        self._beam_provider = beam_provider
        self._offset_provider = offset_provider

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

        status_box = QHBoxLayout()
        status_box.addStretch()
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 11px;")
        status_box.addWidget(self._status_label)
        viewer_layout.addLayout(status_box)

        self._scene = QGraphicsScene()
        self._scene.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        # scene.changed drives ONLY the thumbnail
        # committing changes is done via the viewer's edit-finished callback,
        # so a drag does not spam writes
        self._scene.changed.connect(self._on_scene_changed)
        self._viewer = AreaViewer(
            self._scene,
            self._status_label.setText,
            self._max_areas,
            on_edit_finished=self._handle_edit_finished,
            decoration_factory=self._build_decorations,
        )
        self._viewer.setFixedHeight(self._EXPANDED_HEIGHT)
        self._viewer.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        viewer_layout.addWidget(self._viewer)
        outer.addWidget(self._viewer_container)

    def on_app_state_changed(self, state: AppState) -> None:
        """
        Allow loading an image only while the workflow is not using the microscope.

        Independent of read-only mode: in danger mode the areas can be edited
        during a run, but acquiring an image would drive the microscope from
        the GUI thread at the same time as the workflow.

        Args:
            state: The new application state.
        """
        self._acquisition_allowed = not state.is_running
        self._update_load_button()

    def set_overlays(self, overlays: Sequence[tuple[AreaOverlay, OverlayData]]) -> None:
        """
        Replace the decorations drawn on every area and redraw them live.

        Areas that no longer fit the frame together with the new overlays'
        footprint (e.g. after the margin grew) are shrunk to fit, and that
        correction is emitted as a change.

        Args:
            overlays: Overlay kinds paired with their runtime values (e.g.
                margin in nm, arrow direction). An overlay whose values are
                missing is silently not drawn, so a partially configured form
                still shows the overlays that are ready.
        """
        self._overlays = list(overlays)
        if self._refresh_decorations():
            self._emit()

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
        Replace the current areas.

        If no image is loaded yet, the areas are stored as pending and realized
        on the next `convert_image`. No change is emitted, unless an area had to
        be shrunk to fit the frame and the footprint of its overlays: that
        correction is emitted, so the settings match what is shown.

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
            if self._refresh_decorations():
                self._emit()

    def set_read_only(self, read_only: bool) -> None:
        """
        Freeze the areas while leaving navigation and collapse available.

        In read-only mode the user can still expand/collapse, zoom, and pan, but
        cannot load a new image, draw, delete, move, or resize areas. Resize
        handles are hidden, since editing is disabled.

        Args:
            read_only: True to freeze area editing and image loading.
        """
        self._read_only = read_only

        self._update_load_button()
        # toggle stays enabled: collapse/expand is navigation, not editing
        self._viewer.set_read_only(read_only)
        for item in self._scene.items():
            if isinstance(item, ResizableRect):
                item.set_read_only(read_only)

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

            beam = self._resolve_beam()
            offset_x = self._resolve_offset()

            # we only need to apply the offset if it is non-zero
            # in which case we always need to grab a new frame
            if offset_x != 0.0:
                with self._microscope.add_temporary_beam_shift(
                    BeamShift(x=offset_x, y=0), beam
                ):
                    image = beam.grab_frame()
            # otherwise, we can just use the cached image
            else:
                image = beam.get_image()

            self.convert_image(image)
        except Exception as e:
            self._status_label.setText(f"Acquisition failed: {e}")
        finally:
            self._update_load_button()

    def _resolve_beam(self) -> BeamControl:
        """
        Return the beam wrapper to image with.

        Returns:
            The electron or ion beam if the provider names one, otherwise the
            currently active beam.
        """
        assert self._microscope is not None

        beam_type = self._beam_provider() if self._beam_provider is not None else None
        match beam_type:
            case BeamType.ELECTRON:
                return self._microscope.electron_beam
            case BeamType.ION:
                return self._microscope.ion_beam
            case None:
                return self._microscope.beam

    def _resolve_offset(self) -> float:
        """
        Return the x offset to apply while grabbing, in nanometres.

        Returns:
            The declared offset, or 0.0 when none is declared or a declared one
            cannot be resolved. An unresolvable offset is logged, since it means
            the image is grabbed somewhere other than the form intends.
        """
        if self._offset_provider is None:
            return 0.0

        offset_nm = self._offset_provider()
        if offset_nm is None:
            if self._txt_log is not None:
                self._txt_log.warning(
                    "Area selector declares an acquisition offset that could not "
                    "be resolved; grabbing at the current beam position."
                )
            return 0.0
        return offset_nm

    def convert_image(self, image: Image) -> None:
        """
        Display an image, keeping the current areas in place relative to the frame.

        Areas are scene items in pixels of the displayed image, so they are read
        back as relative areas before the image is replaced and re-created in
        pixels of the new one. A reload at a different resolution or aspect
        ratio therefore keeps every area at the same fraction of the frame.

        Args:
            image: The image to display beneath the area overlay.
        """

        arr = np.ascontiguousarray(image.to_8bit())
        h, w = arr.shape[:2]

        # read the areas in the old image's pixels before the size changes;
        # before any image, this returns the pending regions
        regions = self.get_value()

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

        # replace the whole scene: the background and the area rectangles,
        # which are re-created below in pixels of the new image
        for item in list(self._scene.items()):
            if item.parentItem() is None:
                self._scene.removeItem(item)

        # a mipmapped item: Qt's bilinear filter only reads a 2x2 neighbourhood
        # however far the image is minified, so a 6144x4096 frame in an 885 px
        # viewport carries pixel noise through at full amplitude instead of
        # averaging it away
        pixmap_item = MipmapPixmapItem(self._last_pixmap)
        pixmap_item.setZValue(-1)
        self._scene.addItem(pixmap_item)
        self._scene.setSceneRect(QRectF(0, 0, w, h))
        self._viewer.reset_zoom()

        for area in regions:
            self._add_relative_area(area)
        self._pending_regions = []

        self._refresh_decorations()
        self._viewer.set_image_loaded()
        self._status_label.setText(f"Image: {w}×{h} px")

        # write back: areas may have been shrunk to fit the new frame and the
        # footprint of their overlays at the new pixel size
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
        supersample = 2
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
        bounds = QRectF(0, 0, w, h)
        rect = ResizableRect(
            bounds.intersected(
                QRectF(
                    area.origin.x * w,
                    area.origin.y * h,
                    area.width * w,
                    area.height * h,
                )
            ),
            on_edit_finished=self._handle_edit_finished,
        )

        rect.set_read_only(self._read_only)

        self._scene.addItem(rect)
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

    def _build_decorations(self) -> list[AreaDecoration]:
        """
        Build one area's decorations from the current overlays and image scale.

        Returns:
            Fresh decoration instances; each area needs its own.
        """
        return build_decorations(self._overlays, self._pixel_size)

    def _refresh_decorations(self) -> bool:
        """
        Rebuild every rectangle's decorations, then fit each into its new bounds.

        Also reports, as a warning on this field, every overlay that cannot be
        drawn: a configuration the criterion would reject, or a decoration that
        does not fit its area.

        Returns:
            True if any area was resized or moved to fit the frame less the
            footprint of its decorations. The caller decides whether to emit.
        """
        fitted = False
        problems = overlay_problems(self._overlays, self._pixel_size)
        for item in self._scene.items():
            if isinstance(item, ResizableRect):
                item.apply_decorations(self._build_decorations())
                fitted |= item.fit_to_bounds()
                problems.extend(item.decoration_problems())

        unique = list(dict.fromkeys(problems))
        self.set_issue(
            _OVERLAY_ISSUE,
            FieldIssue(Severity.WARNING, "\n".join(unique)) if unique else None,
        )

        self._update_thumbnail()
        return fitted

    def _update_load_button(self) -> None:
        """Enable Load only when areas may be edited and the microscope is free."""
        self._load_btn.setEnabled(not self._read_only and self._acquisition_allowed)
