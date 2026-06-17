# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import re
from pathlib import Path
from typing import Protocol, Self

from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.logging.logging import logging_context
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.error import WorkflowError
from fibsem_maestro.workflow.propagations import PropagationRule, Propagations


class WorkflowState(ActionState):
    action_names: list[str]
    action_types: list[str]
    slice_index: int
    propagations: list[PropagationRule]


class WorkflowCallbacks(Protocol):
    def notify_action_finished(self, finished_action_index: int) -> None: ...
    def notify_slice_finished(self) -> None: ...
    def notify_is_paused(self) -> None: ...
    def is_pause_requested(self) -> bool: ...
    def wait_for_resume(self) -> None: ...


class Workflow:
    def __init__(
        self,
        microscope: Microscope,
        actions: Actions,
        propagations: Propagations,
        context: ActionContext,
    ):
        """
        Orchestrates sequential execution of actions across multiple slices.

        Runs the workflow's action sequence once per slice, executing
        synchronization rules after each action to propagate property
        updates to dependent actions.

        Args:
            microscope: THe microscope instance.
            actions: The sequence of actions to execute each slice.
            propagations: The synchronization rules for property propagation.
            context: The action context for managing slice state.
        """

        self.microscope = microscope
        self.actions = actions
        self.propagations = propagations
        self.ctx = context
        self.callbacks: WorkflowCallbacks | None = None

    def set_callbacks(self, callbacks: WorkflowCallbacks) -> None:
        self.callbacks = callbacks

    @classmethod
    def import_from_dir(
        cls, dir: Path, microscope: Microscope, current_workflow_dir: Path
    ) -> Self:
        # find the latest slice of the workflow
        if not (result := find_subdir_with_largest_int(dir / "workflow", "slice_*")):
            raise WorkflowError("No workflow slice found in directory")
        workflow_path, _ = result

        # load the workflow state
        workflow_state = WorkflowState.from_file(workflow_path / "state.yaml")

        # construct the workflow context
        workflow_ctx = FileActionContext(current_workflow_dir / "workflow", "workflow")

        # load the settings of actions and construct them
        actions = Actions()
        for name, type in zip(workflow_state.action_names, workflow_state.action_types):
            # find the latest slice of the action
            name_with_underscores = name.replace(" ", "_")
            if not (
                result := find_subdir_with_largest_int(
                    dir / name_with_underscores, "slice_*"
                )
            ):
                raise WorkflowError(f"No slice found for action {name}")
            action_slice_path, _ = result

            # load the action settings and construct the action
            ActionCls = ACTION_REGISTRY.get(type)
            action_settings = ActionCls.settings_cls().from_file(
                action_slice_path / "settings.yaml"
            )
            action_ctx = FileActionContext(
                current_workflow_dir / name_with_underscores,
                name,
            )
            actions.append(
                ActionCls(name, microscope, action_settings, action_ctx, actions)
            )

        # build the propagations
        propagations = Propagations.from_rules(
            workflow_state.propagations, workflow_ctx.text_logger.derive("propagations")
        )

        return cls(microscope, actions, propagations, workflow_ctx)

    @classmethod
    def import_from_dir_with_state(cls, dir: Path) -> Self:
        # find the latest slice of the workflow
        if not (result := find_subdir_with_largest_int(dir / "workflow", "slice_*")):
            raise WorkflowError("No workflow slice found in directory")
        workflow_path, workflow_slice_number = result

        # load the workflow state and construct the workflow context
        workflow_state = WorkflowState.from_file(workflow_path / "state.yaml")
        workflow_ctx = FileActionContext(
            dir / "workflow", "workflow", slice=workflow_slice_number
        )

        # load the microscope settings and construct the microscope
        microscope_settings = MicroscopeSettings.from_file(
            workflow_path / "microscope_settings.yaml"
        )
        microscope = Microscope(
            microscope_settings,
            ContextualTextLogger(fallback=workflow_ctx.text_logger).derive(
                "microscope"
            ),
        )

        # load the settings of actions and construct them
        actions = Actions()
        for name, type in zip(workflow_state.action_names, workflow_state.action_types):
            # find the latest slice of the action
            name_with_underscores = name.replace(" ", "_")
            if not (
                result := find_subdir_with_largest_int(
                    dir / name_with_underscores, "slice_*"
                )
            ):
                raise WorkflowError(f"No slice found for action {name}")
            action_slice_path, action_slice_number = result

            # load the action settings
            ActionCls = ACTION_REGISTRY.get(type)
            action_settings = ActionCls.settings_cls().from_file(
                action_slice_path / "settings.yaml"
            )
            action_ctx = FileActionContext(
                dir / name_with_underscores, name, slice=action_slice_number
            )

            # construct the action
            action = ActionCls(name, microscope, action_settings, action_ctx, actions)

            # load the action's state
            action.set_state(
                action.ctx.state_store.read("state.yaml", action.state_cls())
            )

            actions.append(action)

        # build the propagations
        propagations = Propagations.from_rules(
            workflow_state.propagations, workflow_ctx.text_logger.derive("propagations")
        )

        return cls(microscope, actions, propagations, workflow_ctx)

    def run(self, n_slices: int) -> None:
        """
        Runs the full acquisition workflow.

        Args:
            n_slices: The number of slices to acquire.
        """
        with logging_context(self.ctx.text_logger):
            if self.ctx.slice == 0:
                # if this is slice 0, initialize all actions
                for action in self.actions:
                    action.initialize_first_slice()
                self.ctx.advance()

            for _ in range(n_slices):
                self._run_slice()

    def _run_slice(self) -> None:
        """Executes all actions for a single slice and performs synchronization."""
        self.ctx.text_logger.info(f"Starting slice {self.ctx.slice}.")
        for i, action in enumerate(self.actions):
            # execute the action
            action.execute()

            # store the state and the current settings of the action
            action.ctx.state_store.next.write("state.yaml", action.state)
            action.ctx.settings_store.next.write("settings.yaml", action.settings)

            # propagate properties to other actions
            self.propagations.propagate(action, self.actions)

            # advance the slice counter for the action
            self.ctx.text_logger.debug(
                f"Advancing slice counter for action '{action.name}'."
            )
            action.ctx.advance()

            if self.callbacks:
                self.callbacks.notify_action_finished(i)

            if self.callbacks and self.callbacks.is_pause_requested():
                # all actions should wait for their background threads to finish
                for action in self.actions:
                    action.wait_for_background_threads()
                # then we notify that the workflow is actually paused
                self.callbacks.notify_is_paused()
                # and wait for the resume signal
                self.callbacks.wait_for_resume()

        # at the end of each slice, increment the workflow slice counter
        self.ctx.advance()
        # store the state of the workflow and the microscope settings
        self.ctx.state_store.write("state.yaml", self.state)
        self.ctx.settings_store.write(
            "microscope_settings.yaml", self.microscope.settings
        )
        # verify consistency of the slice counter with actions
        for action in self.actions:
            if self.ctx.slice != action.ctx.slice:
                raise WorkflowError(
                    f"Desynchronization: workflow slice counter and '{action.name}' slice counter are out of sync"
                )

        if self.callbacks:
            self.callbacks.notify_slice_finished()

    @property
    def state(self) -> WorkflowState:
        return WorkflowState(
            action_names=[action.name for action in self.actions],
            action_types=[
                ACTION_REGISTRY.key_of(type(action)) for action in self.actions
            ],
            slice_index=self.ctx.slice,
            propagations=self.propagations.rules,
        )


def find_subdir_with_largest_int(
    directory: str | Path, pattern: str
) -> tuple[Path, int] | None:
    """
    Find the subdirectory matching a glob pattern that contains the largest
    integer value in its name.

    Args:
        directory: The parent directory to search in.
        pattern:   Glob pattern to filter subdirectories (e.g. "slice_*").

    Returns:
        A (path, largest_int) tuple for the matching subdirectory with the
        largest integer in its name, or None if no matches are found.

    Raises:
        NotADirectoryError: If `directory` does not exist or is not a directory.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a valid directory: {directory}")

    best_path: Path | None = None
    best_value: int | None = None

    for subdir in directory.glob(pattern):
        if not subdir.is_dir():
            continue

        integers = [int(m) for m in re.findall(r"\d+", subdir.name)]
        if not integers:
            continue

        candidate = max(integers)
        if best_value is None or candidate > best_value:
            best_value = candidate
            best_path = subdir

    if best_path is None or best_value is None:
        return None

    return best_path, best_value
