# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QGroupBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.action_panel._rule_widget import PropagationRuleWidget
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.propagations import PropagationRule, Propagations
from fibsem_maestro.workflow.workflow import Workflow


class PropagationsWidget(QGroupBox):
    """
    Editable list of propagation rules for a single parent action.

    Args:
        propagations: The Propagations manager for the whole workflow.
        current_action_name: The name of the action whose rules are shown.
        all_action_names: All action names in the workflow.
        form_builder: FormBuilder instance passed to each rule widget.
        microscope: Microscope instance passed to each rule widget.
    """

    def __init__(
        self,
        current_action: Action,
        workflow: Workflow,
        propagations: Propagations,
        form_builder: FormBuilder,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Propagations", parent)
        self._workflow = workflow
        self._microscope = workflow.microscope
        self._current_action = current_action
        self._form_builder = form_builder
        self._rule_widgets: list[PropagationRuleWidget] = []

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(6)

        # populate existing rules for this action
        for rule in propagations.rules:
            if rule.parent_name == self._current_action.name:
                self._insert_rule_widget(rule)

        self._add_btn = QPushButton("+ Add rule")
        self._add_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._add_btn.clicked.connect(self._add_rule)
        self._layout.addWidget(self._add_btn)

    def _insert_rule_widget(self, rule: PropagationRule) -> None:
        """Insert a rule widget before the Add button."""
        widget = PropagationRuleWidget(
            rule=rule,
            current_action=self._current_action,
            workflow=self._workflow,
            on_remove=self._remove_rule,
            form_builder=self._form_builder,
        )
        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._rule_widgets.append(widget)

    def _add_rule(self) -> None:
        rule = PropagationRule(
            parent_name=self._current_action.name,
            dependent_names=[],
            props_to_propagate=PropertyNames(),
        )
        self._workflow.propagations.rules.append(rule)
        self._insert_rule_widget(rule)

    def _remove_rule(self, widget: PropagationRuleWidget) -> None:
        self._workflow.propagations.rules.remove(widget.rule)
        self._layout.removeWidget(widget)
        widget.deleteLater()
        self._rule_widgets.remove(widget)
