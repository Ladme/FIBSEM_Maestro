# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.gui.form_builder.widgets.field_label import FieldLabel
from fibsem_maestro.gui.form_builder.widgets.group_box import GroupBoxWidget
from fibsem_maestro.gui.workflow_manager import WorkflowManager
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import PropagationRule


class PropagationRuleWidget(QFrame):
    """
    Displays and allows editing of a single Propagation rule.
    """

    def __init__(
        self,
        rule: PropagationRule,
        workflow_manager: WorkflowManager,
        current_action: Action,
        on_remove: Callable,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.rule = rule
        self._current_action = current_action
        self._manager = workflow_manager

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setProperty("dataclass_form", True)

        # outer row: number label + rule box
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        # rule box
        box = QFrame()
        box.setProperty("dataclass_form", True)
        box.setFrameShape(QFrame.Shape.StyledPanel)
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(8, 8, 8, 8)
        box_layout.setSpacing(4)

        # number label
        label = FieldLabel("propagation rule", box)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(label)
        outer.addWidget(box, stretch=1)

        # remove button
        header = QHBoxLayout()
        header.addStretch()
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(22, 22)
        remove_btn.clicked.connect(lambda: on_remove(self))
        header.addWidget(remove_btn)
        box_layout.addLayout(header)

        # grid layout matching form builder style
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)
        grid.setColumnStretch(1, 1)
        box_layout.addLayout(grid)

        # dependents
        dep_label = QLabel("dependents")
        dep_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._dep_list = QListWidget()
        self._dep_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._dep_list.setStyleSheet("""
            QListWidget::item:selected {
                background: #36678f;
                color: #ffffff;
            }
        """)
        self._dep_list.setMaximumHeight(120)
        self._dep_list.itemSelectionChanged.connect(self._sync_dependents)
        self._populate_dep_list(self._manager.workflow.actions)
        grid.addWidget(dep_label, 0, 0)
        grid.addWidget(self._dep_list, 0, 1)

        # properties
        self._props_widget = GroupBoxWidget(
            FormBuilder().build_form(PropertyNames(), self._manager)
        )
        prop_label = FieldLabel("properties", self._props_widget)
        prop_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        if rule.props_to_propagate is not None:
            self._props_widget.set_value(rule.props_to_propagate.model_dump())
        for child in self._props_widget.findChildren(QListWidget):
            cast("QListWidget", child).itemSelectionChanged.connect(self._sync_props)
        grid.addWidget(prop_label, 1, 0)
        grid.addWidget(self._props_widget, 1, 1)

        # wire manager signals
        self._manager.actions_changed.connect(self._populate_dep_list)
        self._manager.action_changed.connect(self.on_action_changed)

    def _sync_dependents(self) -> None:
        self.rule.dependent_names = [
            item.data(Qt.ItemDataRole.UserRole).name
            for item in self._dep_list.selectedItems()
        ]

        self._manager.notify_propagations_changed()

    def _sync_props(self) -> None:
        """Sync selected properties back to the rule immediately."""
        self.rule.props_to_propagate = self._props_widget.get_value()
        self._manager.notify_propagations_changed()

    def _populate_dep_list(self, actions: Actions) -> None:
        previously_selected = {
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._dep_list.selectedItems()
        }
        self._dep_list.itemSelectionChanged.disconnect(self._sync_dependents)
        self._dep_list.clear()
        for action in actions:
            if action is self._current_action:
                continue
            item = QListWidgetItem(action.name)
            item.setData(Qt.ItemDataRole.UserRole, action)
            self._dep_list.addItem(item)
            if (
                action in previously_selected
                or action.name in self.rule.dependent_names
            ):
                item.setSelected(True)
        self._dep_list.itemSelectionChanged.connect(self._sync_dependents)

    def on_action_changed(self, action: Action) -> None:
        for i in range(self._dep_list.count()):
            item = self._dep_list.item(i)
            if item is not None and item.data(Qt.ItemDataRole.UserRole) is action:
                item.setText(action.name)
                break

    def set_read_only(self, read_only: bool) -> None:
        self._dep_list.setDisabled(read_only)
        self._props_widget.setDisabled(read_only)
