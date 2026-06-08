# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.propagations import PropagationRule


class PropagationRuleWidget(QFrame):
    """
    Displays and allows editing of a single Propagation rule.

    Args:
        rule: The Propagation rule to display and mutate.
        all_action_names: All action names in the workflow.
        current_action_name: The parent action name.
        on_remove: Callback invoked when the user clicks ×.
    """

    def __init__(
        self,
        rule: PropagationRule,
        current_action_name: str,
        all_action_names: list[str],
        on_remove: Callable,
        form_builder: FormBuilder,
        microscope: Microscope,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.rule = rule
        self.setFrameShape(QFrame.Shape.StyledPanel)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        # header
        header = QHBoxLayout()
        header.addWidget(QLabel("Propagation rule"))
        header.addStretch()
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(22, 22)
        remove_btn.setStyleSheet(
            "QPushButton { border: none; color: #cc4444; font-size: 14px; }"
        )
        remove_btn.clicked.connect(lambda: on_remove(self))
        header.addWidget(remove_btn)
        outer.addLayout(header)

        lists_row = QHBoxLayout()
        lists_row.setSpacing(12)

        # dependents list
        dep_col = QVBoxLayout()
        dep_col.addWidget(QLabel("Dependents:"))

        self._dep_list = QListWidget()
        self._dep_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._dep_list.setStyleSheet("""
            QListWidget::item:selected {
                background: #2d5a4a;
                color: #ffffff;
                border-left: 3px solid #5a9fd4;
            }
        """)
        for action_name in all_action_names:
            if action_name == current_action_name:
                continue
            item = QListWidgetItem(action_name)
            item.setData(Qt.ItemDataRole.UserRole, action_name)
            self._dep_list.addItem(item)
            if action_name in rule.dependent_names:
                item.setSelected(True)

        self._dep_list.itemSelectionChanged.connect(self._sync_dependents)
        dep_col.addWidget(self._dep_list)
        lists_row.addLayout(dep_col)

        # properties form
        prop_col = QVBoxLayout()
        prop_col.addWidget(QLabel("Properties:"))

        self._props_widget = form_builder.build_form(PropertyNames, microscope)

        # prepopulate from existing rule
        if rule.props_to_propagate is not None:
            self._props_widget.set_value(rule.props_to_propagate.model_dump())

        # sync on every change
        for child in self._props_widget.findChildren(QListWidget):
            cast("QListWidget", child).itemSelectionChanged.connect(self._sync_props)

        prop_col.addWidget(self._props_widget)
        lists_row.addLayout(prop_col)

        outer.addLayout(lists_row)

    def _sync_dependents(self) -> None:
        """Sync selected dependents back to the rule immediately."""
        self.rule.dependent_names = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._dep_list.selectedItems()
        ]

    def _sync_props(self) -> None:
        """Sync selected properties back to the rule immediately."""
        self.rule.props_to_propagate = PropertyNames(**self._props_widget.get_value())
