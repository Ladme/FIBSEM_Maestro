# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from fibsem_maestro.action.action import Action
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.logging.logging import logging_context
from fibsem_maestro.workflow.error import WorkflowError
from fibsem_maestro.workflow.links import ActionLinks
from fibsem_maestro.workflow.propagations import Propagations


class Workflow:
    def __init__(
        self,
        actions: list[Action],
        propagations: Propagations,
        links: ActionLinks,
        context: ActionContext,
    ):
        """
        Orchestrates sequential execution of actions across multiple slices.

        Runs the workflow's action sequence once per slice, executing
        synchronization rules after each action to propagate property
        updates to dependent actions.

        Args:
            actions: The ordered sequence of actions to execute each slice.
            propagations: The synchronization rules for property propagation.
            links: The action links for resolving dependencies.
            context: The action context for managing slice state.
        """

        self.actions = actions
        self.propagations = propagations
        self.links = links
        self._ctx = context

    def run(self, n_slices: int) -> None:
        """
        Runs the full acquisition workflow.

        Args:
            n_slices: The number of slices to acquire.
        """
        with logging_context(self._ctx.text_logger):
            # advance the slice counter of all actions
            # this brings us from the initialization slice 0 to slice 1
            for action in self.actions:
                self._ctx.text_logger.debug(
                    f"Finishing initialization for action '{action.name}'."
                )
                action.ctx.advance()
            self._ctx.advance()

            for _ in range(n_slices):
                self._run_slice()

    def _run_slice(self) -> None:
        """Executes all actions for a single slice and performs synchronization."""
        self._ctx.text_logger.info(f"Starting slice {self._ctx.slice}.")
        for action in self.actions:
            # get links to other actions
            links = self.links.resolve(action)

            # execute the action
            action.execute(links)

            # TODO: implementing pausing
            # if paused, wait for all actions to finish their background threads

            # store the state and the current settings of the action
            action.ctx.state_store.next.write("state.yaml", action.state)
            action.ctx.settings_store.next.write("settings.yaml", action.settings)

            # propagate properties to other actions
            self.propagations.propagate(action, self.actions)

            # advance the slice counter for the action
            self._ctx.text_logger.debug(
                f"Advancing slice counter for action '{action.name}'."
            )
            action.ctx.advance()

        # at the end of each slice, increment the slice counter and verify consistency with actions
        self._ctx.advance()
        for action in self.actions:
            if self._ctx.slice != action.ctx.slice:
                raise WorkflowError(
                    f"Desynchronization: workflow slice counter and '{action.name}' slice counter are out of sync"
                )
