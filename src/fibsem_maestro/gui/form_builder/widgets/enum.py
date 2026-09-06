# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from enum import Enum
from typing import TypeVar

from PyQt6.QtWidgets import QWidget

from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollComboBox
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget

T = TypeVar("T")


class EnumWidget(NoScrollComboBox, BaseWidget[T | None]):
    """
    A combo box for selecting one value from a fixed set of choices.

    Args:
        choices: The selectable values.
        default: The value to select initially, if any.
        optional: If True, add a "(none)" entry allowing an empty selection.
        parent: The parent widget, if any.
    """

    def __init__(
        self,
        choices: list[T],
        default: T | None = None,
        optional: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        BaseWidget.__init__(self)
        self._values: list[T | None] = []

        if optional:
            self.addItem("(none)", userData=None)
            self._values.append(None)

        for choice in choices:
            # store the real Python value as userData alongside the display string
            self.addItem(
                choice.value if isinstance(choice, Enum) else str(choice),
                userData=choice,
            )
            self._values.append(choice)

        if default is not None and default in self._values:
            self.setCurrentIndex(self._values.index(default))

        self.setFixedWidth(200)
        self.currentIndexChanged.connect(lambda _: self._emit())

    def get_value(self) -> T | None:
        """
        Return the currently selected value.

        Returns:
            The selected value, or None if "(none)" is selected.
        """

        return self.currentData()

    def set_value(self, value: T | None) -> None:
        """
        Select the given value, if it is among the choices.

        Args:
            value: The value to select. Does nothing if not present.
        """

        if value in self._values:
            self.setCurrentIndex(self._values.index(value))

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable user interaction with the widget.

        Args:
            read_only: If True, disable the widget to prevent changes.
        """
        self.setEnabled(not read_only)
