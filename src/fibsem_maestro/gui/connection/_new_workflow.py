# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from fibsem_maestro.gui.connection._common import CONNECTION_FIELDS
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.gui.form_builder.utils import get_field_infos
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


class NewWorkflowScreen(QWidget):
    """
    Screen for starting a new workflow.

    Shows only the connection fields (control and ip_address) via FormBuilder.
    Pre-fills values from the last used profile if available.

    Args:
        last_profile: The last used MicroscopeSettings, or None.
        form_builder: FormBuilder instance for building the connection form.
    """

    def __init__(
        self,
        last_profile: MicroscopeSettings | None,
        form_builder: FormBuilder,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._form_builder = form_builder

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Microscope connection"))

        all_infos = get_field_infos(MicroscopeSettings)
        connection_infos = [fi for fi in all_infos if fi.name in CONNECTION_FIELDS]

        self._form = form_builder._build_object(
            MicroscopeSettings, last_profile, connection_infos
        )
        layout.addWidget(self._form)

        # pre-fill from last profile
        if last_profile is not None:
            self._form.set_value(
                {
                    "control": last_profile.control,
                    "ip_address": last_profile.ip_address,
                }
            )

        layout.addStretch()

    def get_connection_values(self) -> dict[str, Any]:
        """Return the current connection field values."""
        return self._form.get_value()
