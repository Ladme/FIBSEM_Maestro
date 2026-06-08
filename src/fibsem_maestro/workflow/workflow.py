# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from fibsem_maestro.action.action import Action
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.workflow.links import ActionLinks
from fibsem_maestro.workflow.propagations import Propagations


class Workflow:
    def __init__(
        self,
        slice_context: SliceContext,
        actions: list[Action],
        propagations: Propagations,
        links: ActionLinks,
        txt_log: TextLogger,
    ):
        """
        Orchestrates sequential execution of actions across multiple slices.

        Runs the workflow's action sequence once per slice, executing
        synchronization rules after each action to propagate property
        updates to dependent actions.

        Args:
            slice_context: Tracks the current slice number.
            actions: The ordered sequence of actions to execute each slice.
            synchronizations: The synchronization rules for property propagation.
            txt_log: Logger for debug and info messages.
        """

        self.actions = actions
        self._slice_context = slice_context
        self.propagations = propagations
        self._links = links
        self._txt_log = txt_log

    def run(self, n_slices: int) -> None:
        """
        Runs the full acquisition workflow.

        Args:
            n_slices: The number of slices to acquire.
        """
        for _ in range(n_slices):
            self._run_slice()

    def _run_slice(self) -> None:
        """Executes all actions for a single slice and performs synchronization."""
        self._slice_context.increment()
        self._txt_log.info(f"Starting slice {self._slice_context.current_slice}.")
        for action in self.actions:
            links = self._links.resolve(action)
            action.execute(self._slice_context.current_slice or 0, links)
            self.propagations.propagate(action, self.actions)
