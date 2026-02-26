# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from pathlib import Path

from nicegui import ui


class SaveFileDialog:
    def __init__(self, on_save: Callable[[Path], None]):
        self.on_save = on_save
        self.current_dir = Path.cwd()

        with ui.dialog() as self.dialog, ui.card().classes("w-96"):
            ui.label("Save settings").classes("text-lg font-bold")

            self.path_label = ui.label()

            ui.button("..", on_click=self.go_up)

            self.files_column = ui.column()

            self.filename = ui.input("File name", value="settings.yaml")

            ui.button("Save", on_click=self.save)

        self.refresh()

    def open(self) -> None:
        self.dialog.open()

    def refresh(self) -> None:
        self.path_label.set_text(str(self.current_dir))
        self.files_column.clear()

        with self.files_column:
            for p in sorted(self.current_dir.iterdir()):
                if p.is_dir():
                    ui.button(
                        f"📁 {p.name}", on_click=lambda _, path=p: self.enter_dir(path)
                    ).props("flat").classes("normal-case text-left")

    def enter_dir(self, path: Path) -> None:
        self.current_dir = path
        self.refresh()

    def go_up(self) -> None:
        self.current_dir = self.current_dir.parent
        self.refresh()

    def save(self) -> None:
        full_path = self.current_dir / self.filename.value
        self.dialog.close()
        self.on_save(full_path)
