# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The editor of one propagation rule: its dependents and the properties it propagates."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.ui.app.errors import NotAllowedError
from fibsem_maestro.ui.forms.editors.collapsible_box import ClickableLabel
from fibsem_maestro.ui.forms.editors.field_label import FieldLabel
from fibsem_maestro.ui.forms.editors.group import GroupWrapper
from fibsem_maestro.ui.forms.issues import FieldValidationError

if TYPE_CHECKING:
    from PyQt6.QtGui import QResizeEvent

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.commands import AppCommands
    from fibsem_maestro.ui.app.session import WorkflowSession
    from fibsem_maestro.ui.forms.builder import FormBuilder
    from fibsem_maestro.ui.forms.context import FormContext
    from fibsem_maestro.workflow.propagations import PropagationRule


class RuleEditor(QFrame):
    """
    Displays and allows editing of a single propagation rule.

    Every edit goes through `AppCommands`; the rule object is only read.

    Args:
        rule: The rule (one of the session's rules, edited in place by it).
        parent_action: The action whose panel holds the editor (the rule's parent).
        session: The workflow session, for queries only.
        commands: Every user intent.
        form_builder: Builds the properties form.
        form_context: The environment of the properties form.
        parent: Parent widget.
    """

    remove_requested = pyqtSignal()
    """The user clicked "×"."""

    def __init__(
        self,
        rule: PropagationRule,
        parent_action: Action,
        session: WorkflowSession,
        commands: AppCommands,
        form_builder: FormBuilder,
        form_context: FormContext,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._rule = rule
        self._parent_action = parent_action
        self._session = session
        self._commands = commands
        self._collapsed = False

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setProperty("dataclass_form", True)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        box = QFrame()
        box.setProperty("dataclass_form", True)
        box.setFrameShape(QFrame.Shape.StyledPanel)
        box_layout = QVBoxLayout(box)
        box_layout.setContentsMargins(8, 8, 8, 8)
        box_layout.setSpacing(4)

        label = FieldLabel("propagation rule", box)
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(label)
        outer.addWidget(box, stretch=1)

        header = QHBoxLayout()
        self._toggle = ClickableLabel("⯆", box)
        self._toggle.setFixedSize(20, 20)
        self._toggle.setStyleSheet(
            "color: #8a8a8a; font-size: 12px; border: none; background: transparent;"
        )
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.clicked.connect(self._on_toggle)
        header.addStretch()

        self._remove_btn = QPushButton("×")
        self._remove_btn.setFixedSize(22, 22)
        self._remove_btn.clicked.connect(self.remove_requested)
        header.addWidget(self._remove_btn)
        box_layout.addLayout(header)

        self._body = QWidget()
        grid = QGridLayout(self._body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)
        grid.setColumnStretch(1, 1)
        box_layout.addWidget(self._body)

        self._dep_list = QListWidget()
        self._dep_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self._dep_list.setStyleSheet("""
            QListWidget::item:selected {
                background: #36678f;
                color: #ffffff;
            }
        """)
        self._dep_list.setMaximumHeight(120)
        self._dep_list.itemSelectionChanged.connect(self._on_dependents_selected)
        self._populate_dep_list()

        dep_label = FieldLabel("dependents", self._dep_list)
        dep_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        grid.addWidget(dep_label, 0, 0)
        grid.addWidget(self._dep_list, 0, 1)

        self._props_form = form_builder.build_detached(PropertyNames, form_context)
        if rule.props_to_propagate is not None:
            self._props_form.set_value(rule.props_to_propagate.model_dump())

        # connected after the initial value, so showing it commits nothing
        self._props_form.changed.connect(self._on_properties_changed)
        self._props_widget = GroupWrapper(self._props_form.widget)
        prop_label = FieldLabel("properties", self._props_widget)
        prop_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        grid.addWidget(prop_label, 1, 0)
        grid.addWidget(self._props_widget, 1, 1)
        self._toggle.raise_()

        session.structure_changed.connect(self._populate_dep_list)
        session.action_renamed.connect(self._populate_dep_list)

    @property
    def rule(self) -> PropagationRule:
        """The rule this editor shows."""
        return self._rule

    @property
    def collapsed(self) -> bool:
        """Whether the rule's fields are hidden."""
        return self._collapsed

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable editing the rule.

        Args:
            read_only: If True, nothing can be edited or removed.
        """
        self._dep_list.setDisabled(read_only)
        self._props_widget.setDisabled(read_only)
        self._remove_btn.setDisabled(read_only)

    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        """Keep the toggle pinned to the top-left corner of the rule box."""
        self._toggle.move(-2, 0)
        if a0 is not None:
            super().resizeEvent(a0)

    def _on_toggle(self) -> None:
        """Collapse or expand the rule's fields, keeping the header visible."""
        self._collapsed = not self._collapsed
        self._toggle.setText("⯈" if self._collapsed else "⯆")
        self._body.setVisible(not self._collapsed)

    def _on_dependents_selected(self) -> None:
        names = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self._dep_list.selectedItems()
        ]
        try:
            self._commands.set_rule_dependents(self._rule, names)
        except NotAllowedError:
            # rules became read-only meanwhile; show the rule as it is
            self._populate_dep_list()

    def _on_properties_changed(self) -> None:
        try:
            names = self._props_form.value()
        except FieldValidationError:
            return
        try:
            self._commands.set_rule_properties(self._rule, names)
        except NotAllowedError:
            # rules became read-only meanwhile; the next change re-sends them all
            return

    def _populate_dep_list(self, *_: object) -> None:
        """List the other actions, selecting the rule's dependents."""
        self._dep_list.blockSignals(True)
        try:
            self._dep_list.clear()
            for action in self._session.actions:
                if action is self._parent_action:
                    continue
                item = QListWidgetItem(action.name)
                item.setData(Qt.ItemDataRole.UserRole, action.name)
                self._dep_list.addItem(item)
                if action.name in self._rule.dependent_names:
                    item.setSelected(True)
        finally:
            self._dep_list.blockSignals(False)
