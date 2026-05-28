# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass

from fibsem_maestro.core.action import Action
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.error import WorkflowError


@dataclass
class Propagation:
    """
    A single propagation rule linking a parent action to its dependents.

    When the parent action finishes execution, the specified microscope
    properties are read from the parent's microscope state and propagated
    to each dependent action's stored properties.

    Attributes:
        parent: The action whose post-execution state is the source of truth.
        dependents: Actions whose stored properties should be updated.
        props_to_propagate: Names of the microscope properties to propagate.
    """

    parent: Action
    dependents: list[Action]
    props_to_propagate: PropertyNames


class Propagations:
    """
    Manages property propagation between actions in a workflow.

    After an action executes, its propagation rules determine which
    microscope properties are propagated to which other actions. The timing
    of the update depends on workflow ordering: dependents that have already
    run in the current slice receive the update for the next slice, while
    dependents that haven't run yet receive it for the current slice.

    Args:
        all_actions: The ordered list of all actions in the workflow.
        txt_log: Logger for debug and info messages.
    """

    def __init__(self, all_actions: list[Action], txt_log: TextLogger):
        self._actions = all_actions
        self._txt_log = txt_log
        self._propagations: list[Propagation] = []

    def register_propagation(
        self,
        from_action: Action,
        to_actions: list[Action],
        props_to_propagate: PropertyNames,
    ) -> None:
        """
        Registers a propagation rule for the given action.

        Args:
            action: The parent action that produces the property updates.
            dependents: Actions that should receive the updated properties.
            props_to_propagate: Names of the properties to propagate.

        Raises:
            WorkflowError: If the action or any dependent is not part of the workflow.
        """
        if from_action not in self._actions:
            raise WorkflowError(f"Action '{from_action.name}' is not defined.")

        for dependent in to_actions:
            if dependent not in self._actions:
                raise WorkflowError(f"Action '{dependent.name}' is not defined.")

        self._propagations.append(
            Propagation(
                parent=from_action,
                dependents=to_actions,
                props_to_propagate=props_to_propagate,
            )
        )

    def propagate(self, action: Action) -> None:
        """
        Executes all propagation rules for the given action.

        Collects the specified microscope properties from the action's
        current state and propagates them to each dependent action's
        stored properties.

        Args:
            action: The action that has just finished executing.

        Raises:
            WorkflowError: If the action is not part of the workflow.
        """
        try:
            index = self._actions.index(action)
        except ValueError:
            raise WorkflowError(f"Action '{action.name}' is not defined.")

        for propagation in self._propagations:
            if propagation.parent == action:
                self._txt_log.debug(
                    f"Propagating properties '{propagation.props_to_propagate}' from '{action.name}' to its dependents."
                )
                props = action.microscope.collect_properties(
                    propagation.props_to_propagate
                )
                self._propagate_to_dependents(index, propagation.dependents, props)

    def _propagate_to_dependents(
        self, index: int, dependents: list[Action], props: GlobalProperties
    ) -> None:
        """
        Propagates properties to dependent actions with correct slice timing.

        Dependents appearing before the parent in the workflow have already
        run this slice, so they receive the update for the next slice.
        Dependents appearing after the parent haven't run yet, so they
        receive the update for the current slice.

        Args:
            index: The position of the parent action in the workflow.
            dependents: The dependent actions to update.
            props: The microscope properties to propagate.
        """
        # update dependents that were run BEFORE the target action
        # properties need to be written for the following slice
        for dependent in self._actions[:index]:
            if dependent in dependents:
                self._txt_log.debug(
                    f"Propagating properties to dependent action '{dependent.name}' for slice {(dependent.props_store.slice or 0) + 1}."
                )
                original_props = dependent.read_properties(dependent.props_store.next)
                original_props.patch(props)
                dependent.write_properties(original_props, dependent.props_store.next)

        # update dependents that were run AFTER the target action
        # properties need to be written for the current slice
        for dependent in self._actions[index + 1 :]:
            if dependent in dependents:
                self._txt_log.debug(
                    f"Propagating properties to dependent action '{dependent.name}' for slice {dependent.props_store.slice}."
                )
                original_props = dependent.read_properties(dependent.props_store)
                original_props.patch(props)
                dependent.write_properties(original_props, dependent.props_store)
