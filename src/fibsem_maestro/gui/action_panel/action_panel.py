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
from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.gui.common import class_name_to_label
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow


class ActionPanel(QWidget):
    """
    A scrollable panel for editing a single Action's settings.

    Binds directly to a live Action instance. The settings form is
    pre-populated from action.settings and writes back to it reactively
    on every change. The propagations section mutates the Propagations
    manager directly.

    Args:
        action: The live action instance to bind to.
        propagations: The Propagations manager for the workflow.
        all_actions: All actions in the workflow.
        microscope: The microscope instance.
        form_builder: FormBuilder instance used to build the settings form.
    """

    def __init__(
        self,
        action: Action,
        workflow: Workflow,
        form_builder: FormBuilder,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._action = action
        self._workflow = workflow
        self._microscope = workflow.microscope

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

        name_label = QLabel(action.name)
        name_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        title_layout.addWidget(name_label)

        type_label = QLabel(f"   > type: {class_name_to_label(type(action).__name__)}")
        type_label.setStyleSheet("font-size: 11px; color: #888888;")
        title_layout.addWidget(type_label)

        beam_label = QLabel(
            f"   > beam: {str(action.beam_type) if action.beam_type is not None else '—'}"
        )
        beam_label.setStyleSheet("font-size: 11px; color: #888888")
        title_layout.addWidget(beam_label)

        layout.addWidget(title_frame)

        # settings
        self._settings_widget = form_builder.build_form(action.settings, self._workflow)
        layout.addWidget(self._settings_widget)

        # propagations
        # self._propagations_widget = _PropagationsWidget(
        #    propagations=propagations,
        #    current_action=action,
        #    all_actions=all_actions,
        #    form_builder=form_builder,
        #    microscope=microscope,
        # )
        # layout.addWidget(self._propagations_widget)

        # collect properties button
        collect_btn = QPushButton("Collect properties")
        collect_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        collect_btn.clicked.connect(self._collect_properties)
        layout.addWidget(collect_btn)

        layout.addStretch()

    def _collect_properties(self) -> None:
        """Call microscope.collect_properties using the action's props_to_collect."""
        try:
            self._microscope.collect_properties(self._action.props_to_collect)
        except Exception as e:
            print(f"collect_properties failed: {e}")

    def on_app_state_changed(self, state: AppState) -> None:
        read_only = state not in {AppState.EDITING, AppState.PAUSED}
        self._settings_widget.set_read_only(read_only)
