# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Any

from PyQt6.QtWidgets import QWidget

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollComboBox
from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper
from fibsem_maestro.workflow.actions import Actions


class ActionSelectWidget(NoScrollComboBox, WidgetWrapper):
    def __init__(
        self,
        actions: Actions,
        type_filter: list[type[Action]],
        default: Any = None,
        optional: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        if optional:
            self.addItem("(none)", userData=None)

        # get all actions matching the type filter
        choices: list[str] = [
            action.name for action in actions if isinstance(action, tuple(type_filter))
        ]

        for choice in choices:
            self.addItem(choice, userData=choice)

        if default is not None:
            idx = self.findData(default)
            if idx >= 0:
                self.setCurrentIndex(idx)
        self.setFixedWidth(200)

    def get_value(self) -> Any:
        return self.currentData()

    def set_value(self, value: Any) -> None:
        idx = self.findData(value)
        if idx >= 0:
            self.setCurrentIndex(idx)

    def set_read_only(self, read_only: bool) -> None:
        self.setEnabled(not read_only)
