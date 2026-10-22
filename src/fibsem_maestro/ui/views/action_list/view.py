# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The ordered list of the workflow's actions, with add, remove, duplicate, reorder and rename."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QModelIndex, QPoint, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.ui.app.errors import (
    ActionRenameError,
    InvalidActionNameError,
    NotAllowedError,
)
from fibsem_maestro.ui.views.action_list.add_dialog import AddActionDialog
from fibsem_maestro.ui.views.action_list.item import ActionListItem, action_item_view
from fibsem_maestro.ui.views.common import horizontal_separator

if TYPE_CHECKING:
    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.action_status import ActionStatus
    from fibsem_maestro.ui.app.commands import AppCommands
    from fibsem_maestro.ui.app.edit_policy import EditPolicy, Permissions
    from fibsem_maestro.ui.app.session import WorkflowSession
    from fibsem_maestro.ui.views.action_list.item import ActionItemViewData


class ActionListView(QWidget):
    """
    Panel containing the ordered list of workflow actions.

    The list mirrors the session's actions and is rebuilt whenever they change,
    keeping the current row. Every change goes through `AppCommands`.

    Args:
        session: The workflow session (actions, rules).
        status: The per-action indicators.
        policy: The permissions (structure edits).
        commands: Every user intent.
        parent: Parent widget.
    """

    current_action_changed = pyqtSignal(object)
    """The selected `Action`, or None when nothing is selected."""

    def __init__(
        self,
        session: WorkflowSession,
        status: ActionStatus,
        policy: EditPolicy,
        commands: AppCommands,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._status = status
        self._policy = policy
        self._commands = commands
        # the action of each row, as of the last rebuild
        self._actions: list[Action] = []
        # True while this view removes an action, so its rebuild keeps a row selected
        self._removing = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # action list
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.currentRowChanged.connect(self._on_current_row_changed)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        self._list.setStyleSheet("""
            QListWidget::item:selected {
                background: #36678f;
                border: none;
            }
        """)
        outer.addWidget(self._list)

        outer.addWidget(horizontal_separator())

        # add button
        self._add_btn = QPushButton("+ Add action")
        self._add_btn.clicked.connect(self._on_add)
        outer.addWidget(self._add_btn)

        self._rebuild()
        self._on_permissions_changed(policy.permissions)

        session.structure_changed.connect(self._rebuild)
        session.action_settings_changed.connect(self._render_items)
        session.action_renamed.connect(self._render_items)
        session.rules_changed.connect(self._render_items)
        status.changed.connect(self._render_items)
        policy.changed.connect(self._on_permissions_changed)

    @property
    def current_action(self) -> Action | None:
        """The selected action, or None."""
        return self._action_at(self._list.currentRow())

    @property
    def list_widget(self) -> QListWidget:
        """The list of items."""
        return self._list

    @property
    def add_button(self) -> QPushButton:
        """The "+ Add action" button."""
        return self._add_btn

    def select(self, action: Action) -> None:
        """
        Make an action the current one.

        Args:
            action: An action of the session.
        """
        for row, candidate in enumerate(self._actions):
            if candidate is action:
                self._list.setCurrentRow(row)
                return

    def item_widget(self, action: Action) -> ActionListItem | None:
        """
        The list item showing an action.

        Args:
            action: An action of the session.

        Returns:
            The item widget, or None if the action is not listed.
        """
        for row, candidate in enumerate(self._actions):
            if candidate is action:
                return self._item_widget(row)
        return None

    def _rebuild(self) -> None:
        """
        Rebuild the list from the session's actions, keeping the current row.

        If the current row no longer exists, nothing is selected; after a
        remove, the row is clamped to the last one instead.
        """
        current_row = self._list.currentRow()
        self._list.clear()
        self._actions = list(self._session.actions)

        renamable = self._policy.permissions.structure_editable
        for action in self._actions:
            item = QListWidgetItem(self._list)
            item_widget = ActionListItem(self._view_data(action))
            item_widget.set_renamable(renamable)
            item_widget.rename_requested.connect(self._on_rename_requested)
            item.setSizeHint(item_widget.sizeHint())
            self._list.setItemWidget(item, item_widget)

        count = self._list.count()
        if self._removing:
            # the old GUI took the item out first, so Qt moved the selection to
            # the row's successor, or to the new last row
            current_row = min(current_row, count - 1)
        self._list.setCurrentRow(current_row if current_row < count else -1)

    def _render_items(self, *_: object) -> None:
        """Re-render every item from the current state (no rebuild)."""
        for row, action in enumerate(self._actions):
            widget = self._item_widget(row)
            if widget is not None:
                widget.render_data(self._view_data(action))

    def _view_data(self, action: Action) -> ActionItemViewData:
        return action_item_view(
            action,
            self._status.indicator(action),
            self._session.dependents_of(action),
        )

    def _on_permissions_changed(self, permissions: Permissions) -> None:
        editable = permissions.structure_editable
        self._add_btn.setEnabled(editable)
        self._list.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
            if editable
            else QAbstractItemView.DragDropMode.NoDragDrop
        )
        for row in range(self._list.count()):
            widget = self._item_widget(row)
            if widget is not None:
                widget.set_renamable(editable)

    def _item_widget(self, row: int) -> ActionListItem | None:
        item = self._list.item(row)
        if item is None:
            return None
        return cast("ActionListItem | None", self._list.itemWidget(item))

    def _action_at(self, row: int) -> Action | None:
        return self._actions[row] if 0 <= row < len(self._actions) else None

    def _on_current_row_changed(self, row: int) -> None:
        self.current_action_changed.emit(self._action_at(row))

    def _on_add(self) -> None:
        dialog = AddActionDialog(
            existing_names={action.name for action in self._session.actions},
            parent=self,
        )
        try:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            action = self._commands.add_action(
                dialog.selected_type_key(), dialog.selected_name()
            )
        finally:
            dialog.deleteLater()
        self.select(action)

    def _on_rows_moved(
        self,
        parent: QModelIndex,
        start: int,
        end: int,
        destination: QModelIndex,
        row: int,
    ) -> None:
        """Move the dragged actions in the workflow; the rebuild mirrors the new order."""
        _ = parent, destination

        # row is the destination index before the source rows are removed,
        # so it overshoots by the block size when the item is dragged downwards
        moved_count = end - start + 1
        final_row = row - moved_count if row > start else row

        self._commands.move_actions(start, moved_count, final_row)

    def _on_context_menu(self, pos: QPoint) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        action = self._action_at(self._list.row(item))
        if action is None:
            return

        menu = QMenu(self)
        editable = self._policy.permissions.structure_editable
        remove_action = menu.addAction("Remove")
        assert remove_action is not None
        remove_action.setEnabled(editable)
        duplicate_action = menu.addAction("Duplicate")
        assert duplicate_action is not None
        duplicate_action.setEnabled(editable)

        chosen = menu.exec(self._list.mapToGlobal(pos))
        menu.deleteLater()

        if chosen == remove_action:
            self._remove_action(action)
        elif chosen == duplicate_action:
            self._commands.duplicate_action(action)

    def _remove_action(self, action: Action) -> None:
        action_dir = self._session.workflow_dir / action.name_with_underscores
        self._removing = True
        try:
            error = self._commands.remove_action(action)
        finally:
            self._removing = False
        if error is not None:
            QMessageBox.warning(
                self,
                "Could not remove action directory",
                f"Action '{action.name}' was removed from the workflow, but its "
                f"data directory could not be deleted:\n\n{action_dir}\n\n{error}\n\n"
                "The directory can be deleted manually. It has no effect on the "
                "workflow.",
            )

    def _on_rename_requested(self, new_name: str) -> None:
        item = self.sender()
        row = next(
            (r for r in range(self._list.count()) if self._item_widget(r) is item),
            -1,
        )
        action = self._action_at(row)
        if action is None or not isinstance(item, ActionListItem):
            return

        old_name = action.name
        try:
            self._commands.rename_action(action, new_name)
        except NotAllowedError:
            # renaming was disabled while the editor was open
            item.reset_name_edit()
        except InvalidActionNameError as e:
            item.reset_name_edit()
            QMessageBox.critical(item, "Invalid name", str(e))
        except ActionRenameError as e:
            item.reset_name_edit()
            QMessageBox.critical(
                item,
                "Could not rename action",
                f"Action '{old_name}' could not be renamed to '{new_name}':\n\n{e}",
            )
        except OSError as e:
            # the rename itself stood (and the list was rebuilt), only saving a
            # file afterwards failed; the item may already be scheduled for deletion
            QMessageBox.critical(
                self,
                "Could not rename action",
                f"Action '{old_name}' was renamed to '{new_name}', but saving the "
                f"workflow failed:\n\n{e}",
            )
