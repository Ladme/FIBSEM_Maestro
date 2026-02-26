# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path

from nicegui import ui

from fibsem_maestro.gui.action_sequence import ActionButton, ActionSequence
from fibsem_maestro.gui.save_file_dialog import SaveFileDialog


class MainView:
    def __init__(self, actions: list[ActionButton]):
        self._actions = ActionSequence(actions, self._show_action)

        self._container = ui.column().classes("w-full")
        self._active_action: ActionButton | None = None

        self._save_dialog = SaveFileDialog(self._save_action_settings)

    def _show_action(self, action: ActionButton) -> None:
        self._container.clear()

        # toggle active action
        if self._active_action == action:
            self._active_action = None
            return

        self._active_action = action

        with self._container:
            self._active_action.settings_form.build()
            self._build_buttons()

    def _build_buttons(self) -> None:
        with ui.row():
            ui.button("Get frame", on_click=None).classes("mt-6")
            ui.button("Save", on_click=self._save_dialog.open).classes("mt-6")

    def _save_action_settings(self, path: Path) -> None:
        if self._active_action is None:
            ui.notify("No action selected.", type="warning")
            return

        self._active_action.settings_form.get_settings().to_file(path)
        ui.notify(f"Saved action {self._active_action.name} to {str(path)}.")
