# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from fibsem_maestro.core.action import Action
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.state.state import State


class Workflow:
    def __init__(self, slice_context: SliceContext):
        self._states: list[State] = []
        self._actions: list[Action] = []
        self._slice_context = slice_context

    def add_state(self, state: State) -> None:
        self._states.append(state)

    def add_action(self, action: Action) -> None:
        self._actions.append(action)

    def run(self, n_slices: int | None = None) -> None:
        for _ in range(n_slices or 1_000_000):
            self._run_slice()
            self._slice_context.increment()

    def _run_slice(self) -> None:
        for action in self._actions:
            # TODO
            # action.execute(self._slice_context.current_slice or 0)
            pass

        for state in self._states:
            state.propagate_to_next()
