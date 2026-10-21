# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""A flat, square, icon-only tool button."""

from PyQt6.QtCore import QEvent, QSize
from PyQt6.QtGui import QIcon, QPalette
from PyQt6.QtWidgets import QToolButton, QWidget

from fibsem_maestro.ui.widgets.icons import render_icon

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
