# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The dialog editing the microscope settings that do not affect the connection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QDialog, QPushButton, QVBoxLayout, QWidget

from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.ui.app.user_config import CONNECTION_FIELDS
from fibsem_maestro.ui.schema.schema import get_field_infos

if TYPE_CHECKING:
    from fibsem_maestro.ui.app.commands import AppCommands
    from fibsem_maestro.ui.app.edit_policy import Permissions
    from fibsem_maestro.ui.app.session import WorkflowSession
    from fibsem_maestro.ui.forms.builder import FormBuilder
    from fibsem_maestro.ui.forms.context import FormContext


class MicroscopeSettingsDialog(QDialog):
    """
    Pop-up dialog for editing internal microscope settings.

    The form edits the live settings of the session's microscope. It is
    read-only unless `permissions.microscope_settings_editable`, evaluated when
    the dialog opens.

    Args:
        session: The workflow session (its microscope).
        commands: Every user intent ("Apply" persists the settings).
        permissions: The permissions when the dialog opens.
        form_builder: Builds the settings form.
        form_context: The environment of the form.
        parent: Parent widget.
    """

    def __init__(
        self,
        session: WorkflowSession,
        commands: AppCommands,
        permissions: Permissions,
        form_builder: FormBuilder,
        form_context: FormContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Microscope settings")
        self.setModal(True)
        self.setMinimumWidth(400)

        self._commands = commands
        settings = session.microscope.settings

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        # only allow changing the fields which do not affect connection
        non_connection_fields = [
            field.name
            for field in get_field_infos(MicroscopeSettings)
            if field.name not in CONNECTION_FIELDS
        ]
        self._form = form_builder.build_live(
            settings, form_context, fields=non_connection_fields
        )
        self._form.set_value(settings.model_dump())

        self._read_only = not permissions.microscope_settings_editable
        self._form.set_read_only(self._read_only)

        layout.addWidget(self._form.widget)

        close_btn = QPushButton("Apply")
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn)

    @property
    def read_only(self) -> bool:
        """Whether the form is read-only (decided when the dialog opened)."""
        return self._read_only

    def done(self, a0: int) -> None:
        """Release the form's hooks on the settings when the dialog closes."""
        self._form.dispose()
        super().done(a0)

    def _on_close(self) -> None:
        self._commands.apply_microscope_settings(save_profile=not self._read_only)
        self.accept()
