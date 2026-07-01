# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QWidget

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.new_form_builder.widgets._no_scroll import NoScrollComboBox
from fibsem_maestro.gui.new_form_builder.widgets.base import BaseWidget
from fibsem_maestro.workflow.actions import Actions


class ActionSelectWidget(NoScrollComboBox, BaseWidget[str | None]):
    def __init__(
        self,
        actions: Actions,
        type_filter: list[type[Action]],
        default: str | None = None,
        optional: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        BaseWidget.__init__(self)
        self._type_filter = type_filter
        self._optional = optional
        self._populate(actions, default)
        self.setFixedWidth(200)
        self.currentIndexChanged.connect(lambda _: self._emit())

    def _populate(self, actions: Actions, default: str | None = None) -> None:
        self.clear()
        if self._optional:
            self.addItem("(none)", userData=None)
        for action in actions:
            if isinstance(action, tuple(self._type_filter)):
                self.addItem(action.name, userData=action)
        if default is not None:
            self.set_value(default)

    def on_actions_changed(self, actions: Actions) -> None:
        current = self.currentData()
        self._populate(actions, current.name if current is not None else None)

    def on_action_changed(self, action: Action) -> None:
        idx = self.findData(action)
        if idx >= 0:
            self.setItemText(idx, action.name)

    def get_value(self) -> str | None:
        action = self.currentData()
        return action.name if action is not None else None

    def set_value(self, value: str | None) -> None:
        for i in range(self.count()):
            action = self.itemData(i)
            if action is not None and action.name == value:
                self.setCurrentIndex(i)
                return

    def set_read_only(self, read_only: bool) -> None:
        self.setEnabled(not read_only)
