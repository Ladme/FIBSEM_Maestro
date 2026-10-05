# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from PyQt6.QtCore import QByteArray, QEvent, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QToolButton, QWidget

ICON_CAPTURE = (
    '<path d="M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>'
    '<path d="M12 3v12"/><path d="M7 10l5 5 5-5"/>'
)
"""Arrow into a tray: store the microscope state."""

ICON_APPLY = (
    '<path d="M4 15v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>'
    '<path d="M12 15V3"/><path d="M7 8l5-5 5 5"/>'
)
"""Arrow out of a tray: apply the stored properties."""

ICON_EDIT = '<path d="M15 4l5 5L9 20H4v-5z"/><path d="M13 6l5 5"/>'
"""Pencil: edit the stored properties."""

ICON_TEST = (
    '<path d="M9 3h6"/>'
    '<path d="M10 3v6L4.5 18.5a1 1 0 0 0 .9 1.5h13.2a1 1 0 0 0 .9-1.5L14 9V3"/>'
    '<path d="M7 15h10"/>'
)
"""Lab flask: test the action outside the acquisition."""

_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
    'stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
    "{body}</svg>"
)

_BUTTON_SIZE = 30  # px
_ICON_SIZE = 18  # px

_STYLESHEET = """
    QToolButton#iconButton {
        border: 1px solid transparent;
        border-radius: 4px;
        background: transparent;
        padding: 0px;
    }
    QToolButton#iconButton:hover {
        border-color: #346792;
        background: rgba(52, 103, 146, 40);
    }
    QToolButton#iconButton:pressed {
        background: rgba(52, 103, 146, 90);
    }
    QToolButton#iconButton:disabled {
        border-color: transparent;
        background: transparent;
    }
"""


def render_icon(
    body: str, color: QColor, size: int, device_pixel_ratio: float
) -> QPixmap:
    """
    Render an icon body as a square pixmap in the given colour.

    Args:
        body: SVG elements drawn on a 24x24 canvas.
        color: Stroke colour.
        size: Logical edge length in pixels.
        device_pixel_ratio: Ratio of physical to logical pixels.

    Returns:
        A transparent pixmap of `size` logical pixels.
    """
    svg = _SVG_TEMPLATE.format(color=color.name(), body=body).encode()
    renderer = QSvgRenderer(QByteArray(svg))  # ty: ignore[invalid-argument-type]

    side = round(size * device_pixel_ratio)
    pixmap = QPixmap(side, side)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    try:
        renderer.render(painter)
    finally:
        painter.end()

    pixmap.setDevicePixelRatio(device_pixel_ratio)
    return pixmap


class IconButton(QToolButton):
    """
    Flat, square, icon-only tool button with a consistent look on every platform.

    The icon is rendered from a built-in SVG body in the palette's button text
    colour, with an explicit disabled variant, and is re-rendered when the
    palette or style changes.

    Args:
        icon_body: SVG elements on a 24x24 canvas, e.g. `ICON_EDIT`.
        tooltip: Help text shown on hover (rich text allowed).
        accessible_name: Name announced by screen readers.
        parent: Parent widget.
    """

    def __init__(
        self,
        icon_body: str,
        tooltip: str,
        accessible_name: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_body = icon_body

        self.setObjectName("iconButton")
        self.setStyleSheet(_STYLESHEET)
        self.setFixedSize(_BUTTON_SIZE, _BUTTON_SIZE)
        self.setIconSize(QSize(_ICON_SIZE, _ICON_SIZE))
        self.setToolTip(tooltip)
        self.setAccessibleName(accessible_name)

        self._refresh_icon()

    def changeEvent(self, a0: QEvent) -> None:
        """Re-render the icon when the palette or style changes."""
        super().changeEvent(a0)
        if a0.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange):
            self._refresh_icon()

    def _refresh_icon(self) -> None:
        """Render normal and disabled variants for common pixel ratios."""
        palette = self.palette()
        normal = palette.color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )
        disabled = palette.color(
            QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText
        )

        icon = QIcon()
        for ratio in sorted({1.0, 2.0, self.devicePixelRatioF()}):
            icon.addPixmap(
                render_icon(self._icon_body, normal, _ICON_SIZE, ratio),
                QIcon.Mode.Normal,
            )
            icon.addPixmap(
                render_icon(self._icon_body, disabled, _ICON_SIZE, ratio),
                QIcon.Mode.Disabled,
            )
        self.setIcon(icon)
