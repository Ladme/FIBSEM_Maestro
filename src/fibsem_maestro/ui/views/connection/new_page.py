# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The start-up dialog's page for starting a new workflow."""

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.ui.app.user_config import CONNECTION_FIELDS
from fibsem_maestro.ui.forms.builder import FormBuilder
from fibsem_maestro.ui.forms.context import FormContext


class NewWorkflowPage(QWidget):
    """
    Page for starting a new workflow.

    Shows only the connection fields of the microscope settings, prefilled from
    the last used profile if there is one.

    Args:
        last_microscope_profile: The last used microscope settings, or None.
        form_builder: Builds the connection form.
        parent: Parent widget.
    """

    def __init__(
        self,
        last_microscope_profile: MicroscopeSettings | None,
        form_builder: FormBuilder,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._last_microscope_profile = last_microscope_profile

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Microscope connection"))

        self._form = form_builder.build_detached(
            MicroscopeSettings, FormContext(), fields=CONNECTION_FIELDS
        )
        layout.addWidget(self._form.widget)

        if last_microscope_profile is not None:
            self._form.set_value(last_microscope_profile)

        layout.addStretch()

    def get_microscope_settings(self) -> MicroscopeSettings:
        """
        The microscope settings to connect with.

        The connection fields come from the form; the other fields from the
        last microscope profile, if there is one, or else their defaults.

        Returns:
            The settings.

        Raises:
            FieldValidationError: If a field of the form is invalid.
            pydantic.ValidationError: If the combined settings are invalid.
        """
        settings = self._form.value()

        # get the non-connection fields from the last profile
        if self._last_microscope_profile is not None:
            original_settings = settings.model_dump()
            original_settings.update(
                self._last_microscope_profile.model_dump(exclude=set(CONNECTION_FIELDS))
            )
            settings = MicroscopeSettings(**original_settings)

        return settings
