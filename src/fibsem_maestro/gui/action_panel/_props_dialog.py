# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.gui.workflow_manager import WorkflowManager
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.properties.global_properties import GlobalProperties

_FORM_STYLESHEET = """
    QWidget[dataclass_form="true"] QWidget[highlighted="true"] {
        border: 1px solid #346792;
        border-radius: 3px;
    }
"""


class PropertiesDialog(QDialog):
    """
    Shows a `GlobalProperties` instance in an editable form.
    """

    def __init__(
        self,
        properties: GlobalProperties,
        workflow_manager: WorkflowManager,
        txt_log: TextLogger,
        parent: QWidget | None = None,
    ) -> None:
        """
        Args:
            properties: The live properties instance to bind the form to. It is
                mutated in place as the user edits.
            workflow_manager: Passed through to the form builder; needed by
                manager-dependent widgets (property/area/action selectors).
            txt_log: Logger used by the form builder for build-time warnings.
            parent: Parent widget.
        """
        super().__init__(parent)

        self._properties = properties

        self.setWindowTitle("Collected properties")
        self.setModal(True)
        self.setGeometry(self.screen().availableGeometry())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        hint = QLabel(
            "Values read from the microscope. Edit them if needed, then save."
        )
        hint.setStyleSheet("font-size: 11px; color: #888888;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(_FORM_STYLESHEET)
        layout.addWidget(scroll)

        self._form = FormBuilder().build_form(
            properties,
            workflow_manager,
            txt_log=txt_log,
            fields=None,
            action=None,
        )
        scroll.setWidget(self._form)

        standard = (
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._buttons = QDialogButtonBox(standard)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        layout.addWidget(self._buttons)

    @property
    def properties(self) -> GlobalProperties:
        """The bound properties instance, including any edits made in the form."""
        return self._properties

    @classmethod
    def review(
        cls,
        properties: GlobalProperties,
        workflow_manager: WorkflowManager,
        txt_log: TextLogger,
        parent: QWidget | None = None,
    ) -> GlobalProperties | None:
        """
        Show the dialog modally and return the reviewed properties.

        Args:
            properties: The live properties instance to review. Mutated in place.
            workflow_manager: Passed through to the form builder.
            txt_log: Logger used by the form builder.
            parent: Parent widget.

        Returns:
            The edited instance if the user accepted, else None. `properties` is
            mutated either way; a None return means the caller should discard it.
        """
        dialog = cls(
            properties=properties,
            workflow_manager=workflow_manager,
            txt_log=txt_log,
            parent=parent,
        )

        if dialog.exec():
            return dialog.properties
        return None
