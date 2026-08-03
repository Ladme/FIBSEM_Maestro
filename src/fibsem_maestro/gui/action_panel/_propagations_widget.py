# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QPushButton, QSizePolicy, QVBoxLayout, QWidget

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.action_panel._rule_widget import PropagationRuleWidget
from fibsem_maestro.gui.form_builder.widgets.collapsible_box import CollapsibleGroupBox
from fibsem_maestro.gui.workflow_manager import WorkflowManager
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.propagations import PropagationRule


class PropagationsWidget(CollapsibleGroupBox):
    """
    Editable list of propagation rules for a single parent action.
    """

    def __init__(
        self,
        current_action: Action,
        workflow_manager: WorkflowManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Propagations", parent)
        self.setStyleSheet("QGroupBox::title { padding-left: 15px; }")
        self._manager = workflow_manager
        self._microscope = self._manager.workflow.microscope
        self._current_action = current_action
        self._rule_widgets: list[PropagationRuleWidget] = []

        # body container so the toggle can hide rules + button together
        self._body = QWidget()
        self._layout = QVBoxLayout(self._body)
        self._layout.setSpacing(10)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 20, 0, 0)
        outer.addWidget(self._body)

        for rule in self._manager.workflow.propagations.rules:
            if rule.parent_name == self._current_action.name:
                self._insert_rule_widget(rule)

        self._add_btn = QPushButton("+ Add rule")
        self._add_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._add_btn.clicked.connect(self._add_rule)
        self._layout.addWidget(self._add_btn)

    def _collapse_body(self) -> QWidget:
        return self._body

    def _insert_rule_widget(self, rule: PropagationRule) -> None:
        """Insert a rule widget before the Add button."""
        widget = PropagationRuleWidget(
            rule=rule,
            workflow_manager=self._manager,
            current_action=self._current_action,
            on_remove=self._remove_rule,
        )
        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._rule_widgets.append(widget)

    def _add_rule(self) -> None:
        rule = PropagationRule(
            parent_name=self._current_action.name,
            dependent_names=[],
            props_to_propagate=PropertyNames(),
        )
        self._manager.workflow.propagations.rules.append(rule)
        self._insert_rule_widget(rule)
        self._manager.notify_propagations_changed()

    def _remove_rule(self, widget: PropagationRuleWidget) -> None:
        self._manager.workflow.propagations.rules.remove(widget.rule)
        self._layout.removeWidget(widget)
        widget.deleteLater()
        self._rule_widgets.remove(widget)
        self._manager.notify_propagations_changed()

    def set_read_only(self, read_only: bool) -> None:
        for widget in self._rule_widgets:
            widget.set_read_only(read_only)

        self._add_btn.setDisabled(read_only)
