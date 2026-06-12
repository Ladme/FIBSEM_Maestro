# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import re
from pathlib import Path
from typing import Self

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.logging.logging import logging_context
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.workflow.error import WorkflowError
from fibsem_maestro.workflow.links import ActionLinks, LinkRule
from fibsem_maestro.workflow.propagations import PropagationRule, Propagations


class WorkflowState(ActionState):
    action_names: list[str]
    action_types: list[str]
    slice_index: int
    propagations: list[PropagationRule]
    links: list[LinkRule]


class Workflow:
    def __init__(
        self,
        microscope: Microscope,
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
            microscope: THe microscope instance.
            actions: The ordered sequence of actions to execute each slice.
            propagations: The synchronization rules for property propagation.
            links: The action links for resolving dependencies.
            context: The action context for managing slice state.
        """

        self.microscope = microscope
        self.actions = actions
        self.propagations = propagations
        self.links = links
        self._ctx = context

    @classmethod
    def import_from_dir(cls, dir: Path) -> Self:
        if not (result := find_subdir_with_largest_int(dir / "workflow", "slice_*")):
            raise WorkflowError("No workflow slice found in directory")
        workflow_path, workflow_slice_number = result

        workflow_state = WorkflowState.from_file(workflow_path / "state.yaml")

        action_slice_numbers: dict[str, int] = {}
        for name in workflow_state.action_names:
            name_with_underscores = name.replace(" ", "_")
            if not (
                result := find_subdir_with_largest_int(
                    dir / name_with_underscores, "slice_*"
                )
            ):
                raise WorkflowError(f"No slice found for action {name}")
            _, action_slice_numbers[name] = result

        return cls._build(
            dir,
            workflow_path,
            workflow_slice_number,
            action_slice_numbers,
            restore_state=False,
        )

    @classmethod
    def import_from_dir_with_state(cls, dir: Path) -> Self:
        if not (result := find_subdir_with_largest_int(dir / "workflow", "slice_*")):
            raise WorkflowError("No workflow slice found in directory")
        workflow_path, workflow_slice_number = result

        workflow_state = WorkflowState.from_file(workflow_path / "state.yaml")

        action_slice_numbers: dict[str, int] = {}
        for name in workflow_state.action_names:
            name_with_underscores = name.replace(" ", "_")
            if not (
                result := find_subdir_with_largest_int(
                    dir / name_with_underscores, "slice_*"
                )
            ):
                raise WorkflowError(f"No slice found for action {name}")
            _, action_slice_numbers[name] = result

        return cls._build(
            dir,
            workflow_path,
            workflow_slice_number,
            action_slice_numbers,
            restore_state=True,
        )

    @classmethod
    def _build(
        cls,
        dir: Path,
        workflow_path: Path,
        workflow_slice_number: int,
        action_slice_numbers: dict[str, int],
        restore_state: bool,
    ) -> Self:
        """
        Construct a Workflow from pre-resolved paths and slice numbers.

        Args:
            dir: Root acquisition directory.
            workflow_path: Path to the workflow slice directory.
            workflow_slice_number: Resolved slice number for the workflow context.
            action_slice_numbers: Mapping from action name to its resolved slice number.
            restore_state: If True, read and apply persisted state for each action.

        Returns:
            A fully constructed Workflow instance.
        """
        workflow_state = WorkflowState.from_file(workflow_path / "state.yaml")
        microscope_settings = MicroscopeSettings.from_file(
            workflow_path / "microscope_settings.yaml"
        )

        workflow_ctx = FileActionContext(
            dir / "workflow", "workflow", slice=workflow_slice_number
        )
        microscope = Microscope(
            microscope_settings,
            ContextualTextLogger(fallback=workflow_ctx.text_logger).derive(
                "microscope"
            ),
        )

        actions: list[Action] = []
        for name, type in zip(workflow_state.action_names, workflow_state.action_types):
            name_with_underscores = name.replace(" ", "_")
            action_slice_number = action_slice_numbers[name]
            action_slice_path = (
                dir / name_with_underscores / f"slice_{action_slice_number}"
            )

            ActionCls = ACTION_REGISTRY.get(type)
            action_settings = ActionCls.settings_cls().from_file(
                action_slice_path / "settings.yaml"
            )
            action_ctx = FileActionContext(
                dir / name_with_underscores, name, slice=action_slice_number
            )
            actions.append(ActionCls(name, microscope, action_settings, action_ctx))

        propagations = Propagations.from_rules(
            workflow_state.propagations, workflow_ctx.text_logger.derive("propagations")
        )
        links = ActionLinks.from_rules(
            workflow_state.links, workflow_ctx.text_logger.derive("links")
        )

        workflow = cls(microscope, actions, propagations, links, workflow_ctx)

        if restore_state:
            for action in actions:
                action_state = action.ctx.state_store.read(
                    "state.yaml", action.state_cls()
                )
                action.set_state(action_state, links.resolve(action))

        return workflow

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

    @property
    def state(self) -> WorkflowState:
        return WorkflowState(
            action_names=[action.name for action in self.actions],
            action_types=[
                ACTION_REGISTRY.key_of(type(action)) for action in self.actions
            ],
            slice_index=self._ctx.slice,
            propagations=self.propagations.rules,
            links=self.links.rules,
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
