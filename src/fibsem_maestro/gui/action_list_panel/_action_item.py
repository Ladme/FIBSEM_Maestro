# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.action_list_panel._indicator_widget import (
    IndicatorMode,
    IndicatorWidget,
)
from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.gui.common import class_name_to_label, validate_action_name
from fibsem_maestro.gui.workflow_manager import WorkflowManager
from fibsem_maestro.workflow.propagations import Propagations


class DoubleClickLabel(QLabel):
    double_clicked = pyqtSignal()

    def mouseDoubleClickEvent(self, a0: QMouseEvent | None) -> None:
        _ = a0
        self.double_clicked.emit()


class ActionItemWidget(QWidget):
    """
    Widget displayed inside each list item.

    Shows a state dot, action name, action type, and propagation badge.
    The name is editable by double-clicking.

    Args:
        action: The action this item represents.
        propagations: The propagations manager, used to count outgoing rules.
    """

    def __init__(
        self,
        action: Action,
        workflow_manager: WorkflowManager,
        workflow_dir: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._action = action
        self._manager = workflow_manager
        self._workflow_dir = workflow_dir

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # state indicator: dot when editing, arrow when running
        self._indicator = IndicatorWidget()
        layout.addWidget(self._indicator)
        self._manager.app_state_changed.connect(self._on_app_state_changed)

        # vertical group: name row + subtitle
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        # name row: name label + propagation badge
        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(6)

        # name label (double-click to edit)
        self._name_label = DoubleClickLabel(action.name)
        self._name_label.setStyleSheet("font-weight: bold;")
        self._name_label.double_clicked.connect(self._start_name_edit)
        name_row.addWidget(self._name_label)

        # inline name editor (hidden by default)
        self._name_edit = QLineEdit(action.name)
        self._name_edit.hide()
        self._name_edit.returnPressed.connect(self._finish_name_edit)
        self._name_edit.editingFinished.connect(self._finish_name_edit)
        name_row.addWidget(self._name_edit)

        # propagation badge
        self._badge = QLabel()
        self._badge.setStyleSheet("color: #5a9fd4; font-size: 11px;")
        name_row.addWidget(self._badge)

        name_row.addStretch()
        text_layout.addLayout(name_row)

        # type + beam subtitle
        self._subtitle_label = QLabel(
            f"{class_name_to_label(type(action).__name__)}  ·  {action.beam_type if action.beam_type is not None else '—'}"
        )
        self._subtitle_label.setStyleSheet("color: #888888; font-size: 10px;")
        text_layout.addWidget(self._subtitle_label)
        self._manager.action_changed.connect(self._on_action_changed)
        self._manager.propagations_changed.connect(self._on_propagations_changed)

        layout.addLayout(text_layout)
        self.update_propagation_badge(self._manager.workflow.propagations)

        self._manager.app_state_changed.connect(self._on_app_state_changed)

    def _on_action_changed(self, action: Action) -> None:
        if self._action is action:
            self._subtitle_label.setText(
                f"{class_name_to_label(type(action).__name__)}  ·  {action.beam_type if action.beam_type is not None else '—'}"
            )

            self._update_indicator()

    def _on_propagations_changed(self, propagations: Propagations) -> None:
        self.update_propagation_badge(propagations)

    def _start_name_edit(self) -> None:
        self._name_label.hide()
        self._name_edit.setText(self._name_label.text())
        self._name_edit.show()
        self._name_edit.setFocus()
        self._name_edit.selectAll()

    def _action_is_prepared(self) -> bool:
        return self._action.ctx.props_store.exists("props.yaml")

    def _finish_name_edit(self) -> None:
        new_name = self._name_edit.text().strip()
        old_name = self._name_label.text()

        if new_name != old_name:
            existing_names = {
                action.name
                for action in self._manager.workflow.actions
                if action.name != old_name
            }
            if (error := validate_action_name(new_name, existing_names)) is not None:
                self._name_edit.setText(old_name)
                QMessageBox.critical(self, "Invalid name", error)
            else:
                self._name_label.setText(new_name)
                # update the action
                self._action.name = new_name
                # update the actions context and move the action directory
                self._action.ctx.change_action_dir(
                    self._workflow_dir / self._action.name_with_underscores
                )

                self._manager.action_changed.emit(self._action)

        self._name_edit.hide()
        self._name_label.show()

    def update_propagation_badge(self, propagations: Propagations) -> None:
        """Recount outgoing propagation rules and update the badge."""
        dependents = list(
            dict.fromkeys(
                d
                for rule in propagations.rules
                if rule.parent_name == self._action.name
                for d in rule.dependent_names
            )
        )
        if dependents:
            self._badge.setText(f"→{len(dependents)}")
            self._badge.setToolTip(f"Propagates to: {', '.join(dependents)}")
            self._badge.show()
        else:
            self._badge.hide()

    @property
    def action(self) -> Action:
        return self._action

    def _on_app_state_changed(self, _: AppState) -> None:
        self._update_indicator()

    def _update_indicator(self, active: bool = False) -> None:
        if self._manager.state == AppState.EDITING:
            self._indicator.set_mode(
                IndicatorMode.CHECK
                if self._action_is_prepared()
                else IndicatorMode.NONE
            )
        else:
            self._indicator.set_mode(
                IndicatorMode.ARROW if active else IndicatorMode.NONE
            )

    def set_active(self, active: bool) -> None:
        self._update_indicator(active=active)
