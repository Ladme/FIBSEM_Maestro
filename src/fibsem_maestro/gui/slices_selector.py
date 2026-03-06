# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import asyncio
from collections.abc import Callable

from nicegui import ui


class SlicesSelector:
    """Dialog for selecting number of slices."""

    def __init__(self, on_confirm: Callable[[int], None]):
        """
        Initialize SlicesSelector.

        Args:
            on_confirm: Callback when user confirms slice count.
        """
        self._on_confirm = on_confirm
        self._slices_input = None
        self._dialog = None

    def open(self) -> None:
        """Open the slices selector dialog."""
        with (
            ui.dialog() as self._dialog,
            ui.column().classes("gap-4 p-4 bg-white rounded shadow-lg"),
        ):
            ui.label("Number of slices").classes("font-semibold")

            self._slices_input = ui.number(
                value=1, min=1, step=1, label="Slices"
            ).classes("w-full")

            with ui.row():
                ui.button("Confirm", on_click=self._handle_confirm).classes("mt-6")
                ui.button("Cancel", on_click=self._dialog.close).classes("mt-6")

        self._dialog.open()

    async def _handle_confirm(self) -> None:
        """Handle confirm button click."""
        assert self._slices_input is not None
        slices = int(self._slices_input.value)
        if self._dialog is not None:
            self._dialog.close()
        ui.notify(f"Running for {slices} slices...")
        await asyncio.to_thread(self._on_confirm, slices)
