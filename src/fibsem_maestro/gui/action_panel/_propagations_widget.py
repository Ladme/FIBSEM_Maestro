# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QGroupBox, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from fibsem_maestro.gui.action_panel._rule_widget import PropagationRuleWidget
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.propagations import PropagationRule, Propagations


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
        propagations: Propagations,
        current_action_name: str,
        all_action_names: list[str],
        form_builder: FormBuilder,
        microscope: Microscope,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Propagations", parent)
        self._propagations = propagations
        self._current_action_name = current_action_name
        self._all_action_names = all_action_names
        self._form_builder = form_builder
        self._microscope = microscope
        self._rule_widgets: list[PropagationRuleWidget] = []

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(6)

        # populate existing rules for this action
        for rule in propagations.rules:
            if rule.parent_name == current_action_name:
                self._insert_rule_widget(rule)

        self._add_btn = QPushButton("+ Add rule")
        self._add_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._add_btn.clicked.connect(self._add_rule)
        self._layout.addWidget(self._add_btn)

    def _insert_rule_widget(self, rule: PropagationRule) -> None:
        """Insert a rule widget before the Add button."""
        widget = PropagationRuleWidget(
            rule=rule,
            current_action_name=self._current_action_name,
            all_action_names=self._all_action_names,
            on_remove=self._remove_rule,
            form_builder=self._form_builder,
            microscope=self._microscope,
        )
        self._layout.insertWidget(self._layout.count() - 1, widget)
        self._rule_widgets.append(widget)

    def _add_rule(self) -> None:
        rule = PropagationRule(
            parent_name=self._current_action_name,
            dependent_names=[],
            props_to_propagate=PropertyNames(),
        )
        self._propagations.rules.append(rule)
        self._insert_rule_widget(rule)

    def _remove_rule(self, widget: PropagationRuleWidget) -> None:
        self._propagations.rules.remove(widget.rule)
        self._layout.removeWidget(widget)
        widget.deleteLater()
        self._rule_widgets.remove(widget)
