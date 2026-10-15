# Released under GPL-3.0 License.
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

        # a default that is not offered selects nothing rather than leaving
        # Qt's automatic first entry, which the settings do not hold
        self._select(default)

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
        Select the given value.

        Args:
            value: The value to select. If it is not among the choices,
                nothing is selected and the widget reads as None, so the
                form never shows a value the settings do not hold.
        """
        self._select(value)

    def _select(self, value: T | None) -> None:
        """
        Select a value, or nothing if it is not among the choices.

        Args:
            value: The value to select; None selects "(none)" if present.
        """
        self.setCurrentIndex(self._values.index(value) if value in self._values else -1)

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable user interaction with the widget.

        Args:
            read_only: If True, disable the widget to prevent changes.
        """
        self.setEnabled(not read_only)
