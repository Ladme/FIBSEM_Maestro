# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from typing import Self

from pydantic.dataclasses import dataclass

from fibsem_maestro.action.action import Action
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.error import WorkflowError


@dataclass
class PropagationRule:
    """
    A single propagation rule linking a parent action to its dependents.

    Attributes:
        parent_name: Name of the action that is the source of truth.
        dependent_names: Names of actions that should receive the updated properties.
        props_to_propagate: Names of the microscope properties to propagate.
    """

    parent_name: str
    dependent_names: list[str]
    props_to_propagate: PropertyNames


class Propagations:
    """
    Manages property propagation between actions in a workflow.

    After an action executes, its propagation rules determine which
    microscope properties are propagated to which other actions. The timing
    of the update depends on workflow ordering: dependents that have already
    run in the current slice receive the update for the next slice, while
    dependents that haven't run yet receive it for the current slice.
    """

    def __init__(self) -> None:
        self.rules: list[PropagationRule] = []

    @classmethod
    def from_rules(cls, rules: list[PropagationRule]) -> Self:
        propagations = cls()
        propagations.rules = rules
        return propagations

    def register_rule(
        self,
        parent_name: str,
        dependent_names: list[str],
        props_to_propagate: PropertyNames,
    ) -> None:
        """
        Register a propagation rule.

        Names are resolved when the rule is applied, not here.

        Args:
            parent_name: Name of the action whose produced properties propagate.
            dependent_names: Names of the actions that receive them.
            props_to_propagate: Names of the properties to propagate. Each must
                be in the parent's `properties_to_collect`.
        """
        self.rules.append(
            PropagationRule(parent_name, dependent_names, props_to_propagate)
        )

    def propagate(
        self,
        parent: Action,
        produced: GlobalProperties,
        all_actions: Actions,
        text_logger: TextLogger,
    ) -> None:
        """
        Propagate a parent's produced properties to its dependents.

        Dependents that already ran in this slice receive the update for the
        next slice, and the others for the current slice. This follows from
        each dependent's slice counter.

        Args:
            parent: The action that has just produced properties.
            produced: The properties the parent wrote to its next slice.
            all_actions: The ordered list of all actions in the workflow.
            text_logger: Logger for diagnostics.

        Raises:
            WorkflowError: If a dependent is undefined, or a rule propagates a
                property the parent did not produce.
        """
        actions_by_name = {a.name: a for a in all_actions}

        for rule in self.rules:
            if rule.parent_name != parent.name:
                continue

            try:
                props = produced.select(rule.props_to_propagate)
            except KeyError as e:
                # TODO: add this to GUI hint
                raise WorkflowError(
                    f"Rule propagates {rule.props_to_propagate} from '{parent.name}', "
                    f"but '{parent.name}' did not produce all of them; add them to "
                    f"its properties to collect."
                ) from e

            text_logger.debug(
                f"Propagating properties '{rule.props_to_propagate}' "
                f"from '{parent.name}' to its dependents."
            )

            dependents: list[Action] = []
            for name in rule.dependent_names:
                if name not in actions_by_name:
                    raise WorkflowError(f"Dependent action '{name}' is not defined.")
                dependents.append(actions_by_name[name])

            self._propagate_to_dependents(all_actions, dependents, props, text_logger)

    def _propagate_to_dependents(
        self,
        all_actions: Actions,
        dependents: list[Action],
        props: GlobalProperties,
        text_logger: TextLogger,
    ) -> None:
        dependent_set = set(dependents)

        # due to the way slice advancing works,
        # properties are automatically written for the correct slice
        for dependent in all_actions:
            if dependent not in dependent_set:
                continue

            text_logger.debug(
                f"Propagating to '{dependent.name}' for slice {dependent.ctx.props_store.slice}."
            )
            original_props = dependent.read_properties()
            original_props.patch(props)
            dependent.write_properties(original_props)
