# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QListWidget

from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class MultiSelectWidget(QListWidget, WidgetWrapper):
    def __init__(
        self, choices: list[str], default: list[str] | None = None, parent=None
    ):
        super().__init__(parent)
        WidgetWrapper.__init__(self)
        self.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.setStyleSheet("""
            QListWidget::item:selected {
                background: #2d5a4a;
                color: #ffffff;
            }
            QListWidget::item:selected:hover {
                background: #3a6a5a;
            }
        """)

        for choice in choices:
            self.addItem(choice)
        for text in default or []:
            items = self.findItems(text, Qt.MatchFlag.MatchExactly)
            for item in items:
                item.setSelected(True)

        self.itemSelectionChanged.connect(self._notify_changed)

    def get_value(self) -> list[str]:
        return [item.text() for item in self.selectedItems()]

    def set_value(self, value: list[str]) -> None:
        for i in range(self.count()):
            self.item(i).setSelected(self.item(i).text() in value)

    def set_read_only(self, read_only: bool) -> None:
        self.setEnabled(not read_only)
