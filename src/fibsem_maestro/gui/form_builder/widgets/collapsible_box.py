# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QResizeEvent
from PyQt6.QtWidgets import QGroupBox, QLabel, QWidget


class ClickableLabel(QLabel):
    """
    A QLabel that exposes a clicked signal.

    Emits ``clicked`` on each mouse press.
    """

    clicked = pyqtSignal()

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        """
        Emit `clicked` and forward the event to the base class.

        Args:
            ev: The mouse press event.
        """

        self.clicked.emit()
        super().mousePressEvent(ev)


class CollapsibleGroupBox(QGroupBox):
    """
    A `QGroupBox` with a title-bar toggle that collapses its body.

    Subclasses lay out their content and return the widget to hide from
    `_collapse_body`. The toggle arrow and its position are handled here.

    Args:
        title: The group box title.
        parent: The parent widget, if any.
    """

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._collapsed = False

        self._toggle = ClickableLabel("⯆", self)
        self._toggle.setFixedSize(20, 20)
        self._toggle.setStyleSheet(
            "color: #8a8a8a; font-size: 12px; border: none; background: transparent;"
        )
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.clicked.connect(self._on_toggle_clicked)

    def _collapse_body(self) -> QWidget:
        """
        Return the widget hidden when collapsed.

        Returns:
            The body widget the toggle should show and hide.
        """
        raise NotImplementedError

    def resizeEvent(self, a0: QResizeEvent) -> None:
        """Keep the toggle pinned to the top-left of the group box."""
        self._toggle.move(-2, 5)
        super().resizeEvent(a0)

    def _on_toggle_clicked(self) -> None:
        """Toggle collapsed state, updating the arrow and body visibility."""
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        """
        Collapse or expand the body.

        Args:
            collapsed: True to hide the body, False to show it.
        """
        self._collapsed = collapsed
        self._toggle.setText("⯈" if collapsed else "⯆")
        self._collapse_body().setVisible(not collapsed)
