# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtWidgets import QWidget

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollComboBox
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.workflow.actions import Actions


class ActionSelectWidget(NoScrollComboBox, BaseWidget[str | None]):
    """
    A combo box for selecting an action by name from a filtered list.

    Args:
        actions: The collection of actions to choose from.
        type_filter: Action types to include; actions of other types are omitted.
        default: Name of the action to select initially, if any.
        optional: If True, add a "(none)" entry allowing an empty selection.
        parent: The parent widget, if any.
    """

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
        """
        Rebuild the item list from the given actions.

        Clears existing items, adds an optional "(none)" entry, then adds
        each action matching the type filter. Selects `default`.

        Args:
            actions: The collection of actions to populate from.
            default: Name of the action to select after populating, if any.
        """

        self.clear()
        if self._optional:
            self.addItem("(none)", userData=None)
        for action in actions:
            if isinstance(action, tuple(self._type_filter)):
                self.addItem(action.name, userData=action)

        self.set_value(default)

    def on_actions_changed(self, actions: Actions) -> None:
        """
        Called when the set of available actions changes.

        Repopulates the widget while preserving the current selection. Notifies
        once, and only if the selection changed, e.g. because the selected
        action was removed.

        Args:
            actions: The updated collection of actions.
        """

        current = self.currentData()
        # rebuilding passes through transient selections that must not be written
        with QSignalBlocker(self):
            self._populate(actions, current.name if current is not None else None)
        if self.currentData() is not current:
            self._emit()

    def on_action_changed(self, action: Action) -> None:
        """
        Called when a single action is changed.

        Updates the displayed name of the action if it is present.

        Args:
            action: The action that changed.
        """

        idx = self.findData(action)
        if idx >= 0:
            self.setItemText(idx, action.name)

    def get_value(self) -> str | None:
        """
        Return the name of the currently selected action.

        Returns:
            The selected action's name, or None if no action is selected.
        """

        action = self.currentData()
        return action.name if action is not None else None

    def set_value(self, value: str | None) -> None:
        """
        Select the action with the given name.

        If no such action is offered, nothing is selected ("(none)" for an
        optional selector given None), so the form never shows a link the
        settings do not hold; the field then reads as None and is marked.

        Args:
            value: The name of the action to select, or None.
        """

        for i in range(self.count()):
            action = self.itemData(i)
            if action is not None and action.name == value:
                self.setCurrentIndex(i)
                return

        self.setCurrentIndex(0 if self._optional and value is None else -1)

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable user interaction with the widget.

        Args:
            read_only: If True, disable the widget to prevent changes.
        """
        self.setEnabled(not read_only)
