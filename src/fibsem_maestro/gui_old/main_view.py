# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from pathlib import Path

from nicegui import ui

from fibsem_maestro.gui.action_sequence import ActionButton, ActionSequence
from fibsem_maestro.gui.save_file_dialog import SaveFileDialog
from fibsem_maestro.gui.slices_selector import SlicesSelector


class MainView:
    def __init__(self, actions: list[ActionButton], run: Callable[[int], None]):
        self._slices_selector = SlicesSelector(run)
        self._actions = ActionSequence(
            actions, self._show_action, self._slices_selector.open
        )

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
            ui.button("Save settings", on_click=self._save_dialog.open).classes("mt-6")
            ui.button(
                "Save microscope properties",
                on_click=self._collect_and_save_microscope_properties,
            ).classes("mt-6")

    def _save_action_settings(self, path: Path) -> None:
        if self._active_action is None:
            ui.notify("No action selected.", type="warning")
            return

        self._active_action.settings_form.get_settings().to_file(path)
        ui.notify(f"Saved action {self._active_action.name} to {str(path)}.")

    def _collect_and_save_microscope_properties(self) -> None:
        if self._active_action is None:
            ui.notify("No action selected.", type="warning")
            return

        action = self._active_action.settings_form.get_action()
        ui.notify(
            f"Collecting microscope properties for action {self._active_action.name}..."
        )
        action.collect_and_write_properties()
        ui.notify("Saved microscope properties.")
