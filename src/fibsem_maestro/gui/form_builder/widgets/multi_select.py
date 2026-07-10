# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QListWidget

from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget


class MultiSelectWidget(QListWidget, BaseWidget[list[str]]):
    """
    A list widget for selecting any number of string choices.

    Displays each choice as a row and allows multiple selections, exposing
    the selected texts as the widget value.

    Args:
        choices: The selectable strings, one per row.
        default: The strings to select initially, if any.
        parent: The parent widget, if any.
    """

    def __init__(
        self, choices: list[str], default: list[str] | None = None, parent=None
    ):
        super().__init__(parent)
        BaseWidget.__init__(self)
        self.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.setStyleSheet("""
            QListWidget::item:selected {
                background: #36678f;
                color: #ffffff;
            }
            QListWidget::item:selected:hover {
                background: #36678f;
            }
        """)

        for choice in choices:
            self.addItem(choice)
        for text in default or []:
            items = self.findItems(text, Qt.MatchFlag.MatchExactly)
            for item in items:
                item.setSelected(True)

        self.itemSelectionChanged.connect(self._emit)

    def get_value(self) -> list[str]:
        """
        Return the currently selected choices.

        Returns:
            The texts of the selected rows, in list order.
        """

        return [item.text() for item in self.selectedItems()]

    def set_value(self, value: list[str]) -> None:
        """
        Set the selection to match the given choices.

        Selects rows whose text is in `value` and deselects the rest.

        Args:
            value: The strings that should be selected.
        """

        for i in range(self.count()):
            self.item(i).setSelected(self.item(i).text() in value)

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable user interaction with the widget.

        Args:
            read_only: If True, disable the widget to prevent changes.
        """
        self.setEnabled(not read_only)
