# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class StringWidget(QWidget, WidgetWrapper):
    def __init__(
        self,
        default: str = "",
        suffix: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._edit = QLineEdit()
        self._edit.setText(str(default) if default else "")
        self._edit.setFixedWidth(200)
        layout.addWidget(self._edit)
        if suffix:
            layout.addWidget(QLabel(suffix))
        layout.addStretch()

    def get_value(self) -> str | None:
        return self._edit.text()

    def set_value(self, value: str | None) -> None:
        self._edit.setText(str(value) if value is not None else "")

    def set_read_only(self, read_only: bool) -> None:
        self._edit.setReadOnly(read_only)
