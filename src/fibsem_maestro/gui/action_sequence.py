# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable

from nicegui import ui

from fibsem_maestro.gui.settings_form.settings_form import SettingsForm


class ActionButton:
    def __init__(self, name: str, settings_form: SettingsForm):
        self.name = name
        self.settings_form = settings_form


class ActionSequence:
    def __init__(
        self,
        actions: list[ActionButton],
        on_action_click: Callable[[ActionButton], None],
    ):
        self._actions = actions
        self._external_click_handler = on_action_click
        self._selected_action: ActionButton | None = None

        self._row = ui.row().classes("gap-2")
        self.render()

    def render(self) -> None:
        self._row.clear()
        with self._row:
            for action in self._actions:
                selected = action == self._selected_action

                color = "positive" if selected else "primary"
                ui.button(action.name).props(f"color={color} unelevated").classes(
                    "px-6 py-3 text-white rounded font-semibold"
                ).on_click(lambda _, a=action: self._handle_click(a))

    def _handle_click(self, action: ActionButton) -> None:
        # toggle selection
        if self._selected_action == action:
            self._selected_action = None
        else:
            self._selected_action = action

        # notify external controller
        self._external_click_handler(action)

        # redraw to update button colors
        self.render()
