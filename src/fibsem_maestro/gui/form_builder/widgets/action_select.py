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
        self._type_filter = type_filter
        self._optional = optional
        self._populate(actions, default)
        self.setFixedWidth(200)

    def _populate(self, actions: Actions, default: Any = None) -> None:
        self.clear()
        if self._optional:
            self.addItem("(none)", userData=None)
        for action in actions:
            if isinstance(action, tuple(self._type_filter)):
                self.addItem(action.name, userData=action)
        if default is not None:
            idx = self.findData(default)
            if idx >= 0:
                self.setCurrentIndex(idx)

    def on_actions_changed(self, actions: Actions) -> None:
        self._populate(actions, self.currentData())

    def on_action_changed(self, action: Action) -> None:
        idx = self.findData(action)
        if idx >= 0:
            self.setItemText(idx, action.name)

    def get_value(self) -> Any:
        action = self.currentData()
        return action.name if action is not None else None

    def set_value(self, value: Any) -> None:
        for i in range(self.count()):
            action = self.itemData(i)
            if action is not None and action.name == value:
                self.setCurrentIndex(i)
                return

    def set_read_only(self, read_only: bool) -> None:
        self.setEnabled(not read_only)
