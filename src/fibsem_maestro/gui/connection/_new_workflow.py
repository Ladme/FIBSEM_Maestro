# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from fibsem_maestro.gui.connection._common import CONNECTION_FIELDS
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


class NewWorkflowScreen(QWidget):
    """
    Screen for starting a new workflow.

    Shows only the connection fields (control and ip_address) via FormBuilder.
    Pre-fills values from the last used profile if available.

    Args:
        last_microscope_profile: The last used MicroscopeSettings, or None.
        form_builder: FormBuilder instance for building the connection form.
    """

    def __init__(
        self,
        last_microscope_profile: MicroscopeSettings | None,
        form_builder: FormBuilder,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._form_builder = form_builder
        self._last_microscope_profile = last_microscope_profile

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Microscope connection"))

        self._form = form_builder.build_fields(
            MicroscopeSettings, fields=list(CONNECTION_FIELDS)
        )
        layout.addWidget(self._form)

        if last_microscope_profile is not None:
            self._form.set_value(last_microscope_profile)

        layout.addStretch()

    def get_microscope_settings(self) -> MicroscopeSettings:
        """
        Return the current MicroscopeSettings from the form.

        Non-connection attributes are filled based on the last microscope profile,
        if available, or set to their default values.

        Raises:
            Exception: If any of the form fields are invalid.

        """
        settings = self._form.get_value()

        # get the non-connection fields from the last profile
        if self._last_microscope_profile is not None:
            original_settings = settings.model_dump()
            original_settings.update(
                self._last_microscope_profile.model_dump(exclude=CONNECTION_FIELDS)
            )
            settings = MicroscopeSettings(**original_settings)

        return settings
