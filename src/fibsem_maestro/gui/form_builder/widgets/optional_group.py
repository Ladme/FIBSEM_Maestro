# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

from PyQt6.QtWidgets import QCheckBox, QGroupBox, QSizePolicy, QVBoxLayout, QWidget

from fibsem_maestro.gui.form_builder.widgets.object import ObjectWidget
from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class OptionalGroupWidget(QWidget, WidgetWrapper):
    def __init__(
        self, inner: ObjectWidget, enabled_by_default: bool = False, parent=None
    ):
        super().__init__(parent)
        self._inner = inner
        self._enabled = enabled_by_default

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self._checkbox_standalone = QCheckBox()
        self._group = QGroupBox()
        group_layout = QVBoxLayout(self._group)
        self._checkbox_in_group = QCheckBox()
        self._checkbox_in_group.setChecked(True)
        group_layout.addWidget(self._checkbox_in_group)
        group_layout.addWidget(inner)
        group_layout.addStretch()
        self._group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )

        self._checkbox_standalone.stateChanged.connect(self._on_unchecked_toggled)
        self._checkbox_in_group.stateChanged.connect(self._on_checked_toggled)

        if enabled_by_default:
            self._layout.addWidget(self._group)
        else:
            self._layout.addWidget(self._checkbox_standalone)

    def _on_unchecked_toggled(self, state):
        if state:
            self._enabled = True
            self._checkbox_standalone.setParent(None)  # type: ignore
            self._checkbox_in_group.setChecked(True)
            self._layout.addWidget(self._group)

    def _on_checked_toggled(self, state):
        if not state:
            self._enabled = False
            self._group.setParent(None)  # type: ignore
            self._checkbox_standalone.setChecked(False)
            self._layout.addWidget(self._checkbox_standalone)

    def get_value(self) -> Any:
        return self._inner.get_value() if self._enabled else None

    def set_value(self, value: Any) -> None:
        if value is None:
            self._enabled = False
            self._group.setParent(None)  # type: ignore
            self._checkbox_standalone.setChecked(False)
            self._layout.addWidget(self._checkbox_standalone)
        else:
            self._enabled = True
            self._checkbox_standalone.setParent(None)  # type: ignore
            self._checkbox_in_group.setChecked(True)
            self._layout.addWidget(self._group)
            self._inner.set_value(value)
