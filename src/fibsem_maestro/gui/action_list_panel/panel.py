# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import contextlib
import shutil
from pathlib import Path
from typing import cast

from PyQt6.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.gui.action_list_panel._action_item import ActionItemWidget
from fibsem_maestro.gui.action_list_panel._add_action import AddActionDialog
from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.gui.workflow_manager import WorkflowManager
from fibsem_maestro.workflow.actions import Actions


class ActionListPanel(QWidget):
    """
    Panel containing the ordered list of workflow actions.

    Directly mutates the provided Workflow as actions are added, removed,
    or reordered. Emits action_selected when the user clicks an action.
    """

    action_selected = pyqtSignal(object)  # Action or None

    def __init__(
        self,
        workflow_manager: WorkflowManager,
        workflow_dir: Path,
        app_state: AppState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._manager = workflow_manager
        self._workflow_dir = workflow_dir
        self._microscope = self._manager.workflow.microscope
        self._app_state = app_state

        self._active_action: Action | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # action list
        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._on_context_menu)
        self._list.currentRowChanged.connect(self._on_selection_changed)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        self._list.setStyleSheet("""
            QListWidget::item:selected {
                background: #36678f;
                border: none;
            }
        """)
        outer.addWidget(self._list)

        # separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #444444;")
        outer.addWidget(sep)

        # add button
        self._add_btn = QPushButton("+ Add action")
        self._add_btn.clicked.connect(self._on_add)
        self._add_btn.setEnabled(
            self._app_state
            not in {AppState.RUNNING, AppState.STOPPING, AppState.INTERRUPTED}
        )
        outer.addWidget(self._add_btn)

        # populate from existing workflow actions
        self._rebuild(self._manager.workflow.actions)
        self._manager.actions_changed.connect(self._rebuild)
        self._manager.new_workflow.connect(self._on_new_workflow)
        self._manager.action_finished.connect(self._on_action_finished)

    def _on_new_workflow(self, workflow_dir: Path) -> None:
        """Update the action list if a new workflow is opened."""
        self._workflow_dir = workflow_dir
        self._rebuild(self._manager.workflow.actions)

    def _rebuild(self, actions: Actions) -> None:
        """Rebuild the list from the current workflow actions."""
        current_row = self._list.currentRow()
        self._list.clear()
        for action in actions:
            self._append_item(action)
        self._list.setCurrentRow(current_row)

        if self._active_action is not None:
            for i in range(self._list.count()):
                w = self._item_widget(i)
                if w is not None:
                    w.set_active(w.action is self._active_action)

    def _append_item(self, action: Action) -> QListWidgetItem:
        """Create and append a list item for the given action."""
        item = QListWidgetItem(self._list)
        item_widget = ActionItemWidget(action, self._manager, self._workflow_dir)
        item.setSizeHint(item_widget.sizeHint())
        self._list.addItem(item)
        self._list.setItemWidget(item, item_widget)
        return item

    def _item_widget(self, row: int) -> ActionItemWidget | None:
        item = self._list.item(row)
        return cast("ActionItemWidget", self._list.itemWidget(item))

    def _existing_names(self) -> set[str]:
        return {
            item.action.name
            for i in range(self._list.count())
            if (item := self._item_widget(i)) is not None
        }

    def _build_action(self, type_key: str, name: str, slice_number: int) -> Action:
        """Construct a new Action from the registry with default settings."""
        action_cls = ACTION_REGISTRY.get(type_key)
        settings_cls = action_cls.settings_cls()
        settings = settings_cls()

        action = action_cls(
            name=name,
            microscope=self._microscope,
            settings=settings,
            ctx=FileActionContext(
                action_dir=self._workflow_dir / name.replace(" ", "_"),
                name=name.replace(" ", "_"),
                slice=slice_number,
            ),
            actions=self._manager.workflow.actions,
        )

        # immediately after constructing an action, store its settings and state
        # internal state is not changed in the editing mode, so we do not need to update it
        action.ctx.state_store.write("state.yaml", action.state)
        action.ctx.settings_store.write("settings.yaml", action.settings)

        return action

    def _generate_unique_name(self, base_name: str) -> str:
        """Generate a unique name by appending a number suffix if needed."""
        existing = self._existing_names()
        if base_name not in existing:
            return base_name
        i = 2
        while f"{base_name} {i}" in existing:
            i += 1
        return f"{base_name} {i}"

    def _on_add(self) -> None:
        dialog = AddActionDialog(
            existing_names=self._existing_names(),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        action = self._build_action(
            dialog.selected_type_key(),
            dialog.selected_name(),
            # use the workflow context slice number
            self._manager.workflow.ctx.slice,
        )
        self._manager.workflow.actions.append(action)
        item = self._append_item(action)
        self._list.setCurrentItem(item)
        self.action_selected.emit(action)
        self._manager.notify_actions_changed()

    def _on_selection_changed(self, row: int) -> None:
        widget = self._item_widget(row)
        self.action_selected.emit(widget.action if widget is not None else None)

    def _on_rows_moved(
        self,
        parent: QModelIndex,
        start: int,
        end: int,
        dest: QModelIndex,
        row: int,
    ) -> None:
        """Sync workflow action order after a drag-reorder."""
        _ = parent, dest

        # row is the destination index before the source rows are removed,
        # so it overshoots by the block size when the item is dragged downwards
        moved_count = end - start + 1
        final_row = row - moved_count if row > start else row

        actions = [
            widget.action
            for i in range(self._list.count())
            if (widget := self._item_widget(i)) is not None
        ]
        self._manager.workflow.actions.clear()
        self._manager.workflow.actions.extend(actions)

        self._reconcile_slices(final_row, moved_count)
        self._manager.notify_actions_changed()

    def _reconcile_slices(self, first_row: int, count: int) -> None:
        """
        Clamp the slices of the moved actions to satisfy their new neighbours.

        Args:
            first_row: Index of the first moved action in its new position.
            count: Number of contiguous actions that were moved.
        """
        actions = self._manager.workflow.actions
        last_row = first_row + count - 1

        above = actions[first_row - 1].ctx.slice if first_row > 0 else None
        below = actions[last_row + 1].ctx.slice if last_row + 1 < len(actions) else None

        for action in actions[first_row : last_row + 1]:
            new_slice = clamp_slice(action.ctx.slice, above, below)
            if new_slice != action.ctx.slice:
                action.ctx.set_slice(new_slice)

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        row = self._list.row(item)
        widget = self._item_widget(row)
        if widget is None:
            return

        menu = QMenu(self)
        is_editable = self._app_state not in {
            AppState.RUNNING,
            AppState.STOPPING,
            AppState.INTERRUPTED,
        }
        remove_action = menu.addAction("Remove")
        remove_action.setEnabled(is_editable)
        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.setEnabled(is_editable)

        chosen = menu.exec(self._list.mapToGlobal(pos))

        if chosen == remove_action:
            self._remove_action(row, widget.action)
        elif chosen == duplicate_action:
            self._duplicate_action(widget.action)

    def _remove_action(self, row: int, action: Action) -> None:
        self._list.takeItem(row)
        self._manager.workflow.actions.remove(action)
        self._manager.notify_actions_changed()
        # delete the directory for the action; ignore failures
        with contextlib.suppress(Exception):
            shutil.rmtree(self._workflow_dir / action.name_with_underscores)

    def _duplicate_action(self, action: Action) -> None:
        new_name = self._generate_unique_name(action.name)
        type_key = next(
            key for key in ACTION_REGISTRY if ACTION_REGISTRY.get(key) is type(action)
        )
        new_action = self._build_action(
            type_key, new_name, self._manager.workflow.ctx.slice
        )
        self._manager.workflow.actions.append(new_action)
        self._append_item(new_action)
        self._manager.notify_actions_changed()

    def on_app_state_changed(self, state: AppState) -> None:
        """Called by MainWindow when the application state changes."""
        self._app_state = state
        is_editable = state not in {
            AppState.RUNNING,
            AppState.STOPPING,
            AppState.INTERRUPTED,
        }
        self._add_btn.setEnabled(is_editable)

        self._list.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
            if is_editable
            else QAbstractItemView.DragDropMode.NoDragDrop
        )

        # if the workflow has started running,
        # draw the indicator arrow next to the first action
        if state == AppState.RUNNING:
            self._on_action_finished(self._manager.workflow.actions[0])

    def _on_action_finished(self, action: Action) -> None:
        self._active_action = action
        for i in range(self._list.count()):
            w = self._item_widget(i)
            if w is not None:
                w.set_active(w.action is action)


def clamp_slice(current: int, above: int | None, below: int | None) -> int:
    """
    Clamp a slice index to the range permitted by its neighbours.

    Slice indices are non-increasing down the action list: an action must
    have a slice no greater than the action above it and no less than the
    action below it.

    Args:
        current: The moved action's slice index.
        above: The slice index of the action directly above, or None if the
            moved action is now first.
        below: The slice index of the action directly below, or None if the
            moved action is now last.

    Returns:
        The clamped slice index, unchanged if it already satisfies both bounds.
    """
    clamped = current
    if below is not None:
        clamped = max(clamped, below)
    if above is not None:
        clamped = min(clamped, above)
    return clamped
