# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget


class StringWidget(QWidget, BaseWidget[str | None]):
    """
    A single-line text field for editing a string value.

    Args:
        default: The initial text.
        suffix: A unit label to display after the field, if any.
        parent: The parent widget, if any.
    """

    def __init__(
        self,
        default: str = "",
        suffix: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        BaseWidget.__init__(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._edit = QLineEdit()
        self._edit.setText(str(default) if default else "")
        self._edit.setFixedWidth(200)
        self._edit.textChanged.connect(lambda _: self._emit())
        layout.addWidget(self._edit)
        if suffix:
            layout.addWidget(QLabel(suffix))
        layout.addStretch()

    def get_value(self) -> str | None:
        """
        Return the current text.

        Returns:
            The text in the field, which may be an empty string.
        """

        return self._edit.text()

    def set_value(self, value: str | None) -> None:
        """
        Set the field's text.

        Args:
            value: The text to display; None is shown as an empty string.
        """

        self._edit.setText(str(value) if value is not None else "")

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable editing of the text.

        Args:
            read_only: If True, make the field read-only.
        """
        self._edit.setReadOnly(read_only)
