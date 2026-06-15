# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action.registry import ACTION_REGISTRY


class AddActionDialog(QDialog):
    """
    Small dialog for adding a new action to the workflow.

    Shows a type dropdown populated from ACTION_REGISTRY and a name field
    pre-filled with the registry key. The user can change the name freely.

    Args:
        existing_names: Names already in use, to prevent duplicates.
        parent: Parent widget.
    """

    def __init__(
        self,
        existing_names: set[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._existing_names = existing_names
        self.setWindowTitle("Add action")
        self.setFixedWidth(320)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # type dropdown
        layout.addWidget(QLabel("Type:"))
        self._type_combo = QComboBox()
        for key in sorted(ACTION_REGISTRY):
            self._type_combo.addItem(key)
        self._type_combo.currentTextChanged.connect(self._on_type_changed)
        layout.addWidget(self._type_combo)

        # name field
        layout.addWidget(QLabel("Name:"))
        self._name_edit = QLineEdit()
        self._name_edit.textChanged.connect(self._validate)
        layout.addWidget(self._name_edit)

        # error label
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #cc4444; font-size: 11px;")
        layout.addWidget(self._error_label)

        # ok/cancel
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        layout.addWidget(buttons)

        # pre-fill name from first registry key
        if self._type_combo.count() > 0:
            self._name_edit.setText(self._type_combo.currentText().replace("_", " "))

        self._validate()

    def _on_type_changed(self, key: str) -> None:
        self._name_edit.setText(key.replace("_", " "))
        self._validate()

    def _validate(self) -> None:
        name = self._name_edit.text().strip()
        if not name:
            self._error_label.setText("Name cannot be empty.")
            self._ok_btn.setEnabled(False)
        elif name in self._existing_names:
            self._error_label.setText(f"Name '{name}' is already in use.")
            self._ok_btn.setEnabled(False)
        else:
            self._error_label.setText("")
            self._ok_btn.setEnabled(True)

    def _on_accept(self) -> None:
        self._validate()
        if self._ok_btn.isEnabled():
            self.accept()

    def selected_type_key(self) -> str:
        return self._type_combo.currentText()

    def selected_name(self) -> str:
        return self._name_edit.text().strip()
