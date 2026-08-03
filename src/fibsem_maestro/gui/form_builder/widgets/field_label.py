# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QLabel, QWidget


class FieldLabel(QLabel):
    """
    A label that highlights its paired input widget on hover.

    Args:
        text: The label text.
        paired_widget: The widget to highlight when the label is hovered.
        parent: The parent widget, if any.
    """

    def __init__(
        self,
        text: str,
        paired_widget: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._paired = paired_widget

    def enterEvent(self, event) -> None:
        """
        Highlight the paired widget when the pointer enters the label.

        Args:
            event: The enter event.
        """

        self._paired.setProperty("highlighted", True)
        self._refresh_style(self._paired)
        super().enterEvent(event)

    def leaveEvent(self, a0) -> None:
        """
        Remove the highlight when the pointer leaves the label.

        Args:
            a0: The leave event.
        """

        self._paired.setProperty("highlighted", False)
        self._refresh_style(self._paired)
        super().leaveEvent(a0)

    @staticmethod
    def _refresh_style(widget: QWidget) -> None:
        """
        Re-apply a widget's stylesheet to reflect changed properties.

        Args:
            widget: The widget whose style to refresh.
        """
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
