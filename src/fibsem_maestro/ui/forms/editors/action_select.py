# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Editor selecting one of the workflow's actions by name."""

import contextlib
from collections.abc import Sequence

from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtWidgets import QWidget

from fibsem_maestro.action.action import Action
from fibsem_maestro.ui.forms.editor import FieldEditor
from fibsem_maestro.ui.forms.editors._no_scroll import NoScrollComboBox
from fibsem_maestro.ui.ports import ActionCatalog


class ActionSelectWidget(NoScrollComboBox, FieldEditor[str | None]):
    """
    A combo box for selecting an action by name from a filtered list.

    The list follows the catalog: it is rebuilt when actions are added,
    removed or reordered, and an item is relabelled when its action is renamed.

    Args:
        actions: The workflow's actions.
        type_filter: Action types to include; actions of other types are omitted.
        default: Name of the action to select initially, if any.
        optional: If True, add a "(none)" entry allowing an empty selection.
        parent: The parent widget, if any.
    """

    def __init__(
        self,
        actions: ActionCatalog,
        type_filter: Sequence[type[Action]],
        default: str | None = None,
        optional: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        FieldEditor.__init__(self)
        self._catalog = actions
        self._type_filter = tuple(type_filter)
        self._optional = optional
        self._populate(actions.actions, default)
        self.setFixedWidth(200)
        self.currentIndexChanged.connect(lambda _: self._emit())

        # bound methods: Qt drops these connections when this widget is destroyed
        actions.structure_changed.connect(self._on_structure_changed)
        actions.action_renamed.connect(self._on_action_renamed)

    def detach(self) -> None:
        """
        Stop following the catalog. Idempotent; safe after the widget was destroyed.

        A discarded form's widget lives on until its deferred deletion, and
        must not repopulate (and so emit) on catalog changes meanwhile.
        """
        for signal, slot in (
            (self._catalog.structure_changed, self._on_structure_changed),
            (self._catalog.action_renamed, self._on_action_renamed),
        ):
            # not connected: detached before, or Qt dropped it on destruction
            with contextlib.suppress(TypeError):
                signal.disconnect(slot)

    def _populate(self, actions: Sequence[Action], default: str | None = None) -> None:
        """
        Offer exactly the actions passing the type filter, in order, and select `default`.

        An optional selector also offers "(none)" first. Selecting `default`
        follows `set_value`.

        Args:
            actions: The actions to offer from.
            default: Name of the action to select, if any.
        """
        self.clear()
        if self._optional:
            self.addItem("(none)", userData=None)
        for action in actions:
            if isinstance(action, self._type_filter):
                self.addItem(action.name, userData=action)

        self.set_value(default)

    def _on_structure_changed(self) -> None:
        """
        Repopulate after actions were added, removed, reordered or renamed.

        The current selection is preserved. Notifies once, and only if the
        selection changed, e.g. because the selected action was removed.
        """

        current = self.currentData()
        # rebuilding passes through transient selections that must not be written
        with QSignalBlocker(self):
            self._populate(
                self._catalog.actions, current.name if current is not None else None
            )
        # identity, not name: after an import a different action may carry the
        # same name, and the link must then be re-validated and written
        if self.currentData() is not current:
            self._emit()

    def _on_action_renamed(self, action: Action, old_name: str) -> None:
        """
        Show the new name of a renamed action, if it is listed.

        Args:
            action: The renamed action.
            old_name: Its previous name.
        """
        _ = old_name
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
