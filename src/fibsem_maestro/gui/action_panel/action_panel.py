# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.action_panel._propagations_widget import PropagationsWidget
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.workflow.propagations import Propagations


class ActionPanel(QWidget):
    """
    A scrollable panel for editing a single Action's settings.

    Embeds the action's settings form, an editable propagation rules section,
    and a button to trigger property collection from the microscope.

    All content lives inside a single QScrollArea.

    Args:
        action_name: The display name of the action.
        action_type: The class of the action (used for the type label and settings class).
        settings_cls: The dataclass or Pydantic model class for the action's settings.
        propagations: The Propagations manager for the workflow.
        all_actions: All actions in the workflow.
        microscope: The microscope instance.
        form_builder: A FormBuilder instance used to build the settings form.
    """

    def __init__(
        self,
        action_name: str,
        action_cls: type[Action],
        all_action_names: list[str],
        propagations: Propagations,
        microscope: Microscope,
        form_builder: FormBuilder,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._action_cls = action_cls
        self._action_name = action_name
        self._microscope = microscope
        self._form_builder = form_builder

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QWidget[dataclass_form="true"] QWidget[highlighted="true"] {
                border: 1px solid #5a9fd4;
                border-radius: 3px;
            }
        """)
        outer_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # title
        title_frame = QFrame()
        title_frame.setFrameShape(QFrame.Shape.StyledPanel)
        title_layout = QVBoxLayout(title_frame)
        title_layout.setContentsMargins(8, 6, 8, 6)
        title_layout.setSpacing(2)

        name_label = QLabel(action_name)
        name_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        title_layout.addWidget(name_label)

        type_label = QLabel(action_cls.__name__)
        type_label.setStyleSheet("font-size: 11px; color: #888888;")
        title_layout.addWidget(type_label)

        layout.addWidget(title_frame)

        # settings form
        self._settings_widget = form_builder.build_form(
            action_cls.settings_cls(), microscope
        )
        layout.addWidget(self._settings_widget)

        # propagations
        self._propagations_widget = PropagationsWidget(
            propagations=propagations,
            current_action_name=action_name,
            all_action_names=all_action_names,
            form_builder=form_builder,
            microscope=microscope,
        )
        layout.addWidget(self._propagations_widget)

        # collect properties
        collect_btn = QPushButton("Collect properties")
        collect_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        collect_btn.clicked.connect(self._collect_properties)
        layout.addWidget(collect_btn)

        layout.addStretch()

    def _collect_properties(self) -> None:
        """Call microscope.collect_properties using the action's properties_to_collect."""
        action = self.get_action()
        props = action.props_to_collect
        self._microscope.collect_properties(props)

    def get_action(self) -> Action:
        return self._action_cls(**self._settings_widget.get_values())
