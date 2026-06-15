# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QDialog, QPushButton, QVBoxLayout, QWidget

from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.gui.connection._common import (
    CONNECTION_FIELDS,
    save_last_microscope_profile,
)
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.gui.form_builder.utils import get_field_infos
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.workflow.workflow import Workflow


class MicroscopeSettingsDialog(QDialog):
    """
    Pop-up dialog for editing internal microscope settings.

    Args:
        workflow: The current Workflow instance.
        form_builder: FormBuilder instance for building the settings form.
        app_state: The current application state.
        parent: Parent widget.
    """

    def __init__(
        self,
        workflow: Workflow,
        form_builder: FormBuilder,
        app_state: AppState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Microscope settings")
        self.setModal(True)
        self.setMinimumWidth(400)

        self._workflow = workflow
        self._microscope = workflow.microscope
        self._app_state = app_state

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        # only allow changing the fields which do not affect connection
        non_connection_infos = [
            field
            for field in get_field_infos(MicroscopeSettings)
            if field.name not in CONNECTION_FIELDS
        ]
        self._form = form_builder._build_object(
            MicroscopeSettings, self._microscope.settings, non_connection_infos
        )
        self._form.set_value(self._microscope.settings.model_dump())

        # set the form to be read only, if not in editing or paused state
        read_only = app_state not in {AppState.EDITING, AppState.PAUSED}
        self._form.set_read_only(read_only)

        layout.addWidget(self._form)

        close_btn = QPushButton("Apply")
        close_btn.clicked.connect(self._on_close)
        layout.addWidget(close_btn)

    def _on_close(self) -> None:
        if self._app_state in {AppState.EDITING, AppState.PAUSED}:
            save_last_microscope_profile(self._microscope.settings)
        self.accept()
