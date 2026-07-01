# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QLabel, QWidget


class FieldLabel(QLabel):
    """A label that highlights its paired input widget on hover."""

    def __init__(
        self,
        text: str,
        paired_widget: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._paired = paired_widget

    def enterEvent(self, event) -> None:
        self._paired.setProperty("highlighted", True)
        self._refresh_style(self._paired)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # ty:ignore[invalid-method-override]
        self._paired.setProperty("highlighted", False)
        self._refresh_style(self._paired)
        super().leaveEvent(event)

    @staticmethod
    def _refresh_style(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
