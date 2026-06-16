# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path
from typing import cast

from PyQt6.QtCore import Qt, pyqtSignal
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


class ActionListPanel(QWidget):
    """
    Panel containing the ordered list of workflow actions.

    Directly mutates the provided Workflow as actions are added, removed,
    or reordered. Emits action_selected when the user clicks an action.
    """

    action_selected = pyqtSignal(object)  # emits Action

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
        self._run_dir = workflow_dir / "run"
        self._app_state = app_state

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
        outer.addWidget(self._list)

        # separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #444444;")
        outer.addWidget(sep)

        # add button
        self._add_btn = QPushButton("+ Add action")
        self._add_btn.clicked.connect(self._on_add)
        self._add_btn.setEnabled(self._app_state == AppState.EDITING)
        outer.addWidget(self._add_btn)

        # populate from existing workflow actions
        for action in self._manager.workflow.actions:
            self._append_item(action)

    def _append_item(self, action: Action) -> QListWidgetItem:
        """Create and append a list item for the given action."""
        item = QListWidgetItem(self._list)
        item_widget = ActionItemWidget(action, self._manager)
        item_widget.name_changed.connect(self._on_name_changed)
        item.setSizeHint(item_widget.sizeHint())
        self._list.addItem(item)
        self._list.setItemWidget(item, item_widget)
        return item

    def _item_widget(self, row: int) -> ActionItemWidget | None:
        item = self._list.item(row)
        return cast("ActionItemWidget", self._list.itemWidget(item))

    def _existing_names(self) -> set[str]:
        return {
            self._item_widget(i).action.name
            for i in range(self._list.count())
            if self._item_widget(i) is not None
        }

    def _build_action(self, type_key: str, name: str) -> Action:
        """Construct a new Action from the registry with default settings."""
        action_cls = ACTION_REGISTRY.get(type_key)
        settings_cls = action_cls.settings_cls()
        settings = settings_cls()

        run_dir = self._run_dir
        run_dir.mkdir(parents=True, exist_ok=True)

        return action_cls(
            name=name,
            microscope=self._microscope,
            settings=settings,
            ctx=FileActionContext(
                action_dir=self._workflow_dir / name.replace(" ", "_"),
                name=name.replace(" ", "_"),
            ),
            actions=self._manager.workflow.actions,
        )

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
        action = self._build_action(dialog.selected_type_key(), dialog.selected_name())
        self._manager.workflow.actions.append(action)
        item = self._append_item(action)
        self._list.setCurrentItem(item)
        self.action_selected.emit(action)
        self._manager.notify_workflow_changed()

    def _on_selection_changed(self, row: int) -> None:
        widget = self._item_widget(row)
        if widget is not None:
            self.action_selected.emit(widget.action)

    def _on_rows_moved(self, parent, start, end, dest, row) -> None:
        """Sync workflow action order after a drag-reorder."""
        actions = []
        for i in range(self._list.count()):
            widget = self._item_widget(i)
            if widget is not None:
                actions.append(widget.action)
        self._manager.workflow.actions.clear()
        self._manager.workflow.actions.extend(actions)
        self._manager.notify_workflow_changed()

    def _on_name_changed(self, old_name: str, new_name: str) -> None:
        if new_name in self._existing_names() - {old_name}:
            # revert - name already taken
            for i in range(self._list.count()):
                w = self._item_widget(i)
                if w is not None and w.action.name == old_name:
                    w._name_label.setText(old_name)
            return

        # apply to the action
        for i in range(self._list.count()):
            w = self._item_widget(i)
            if w is not None and w.action.name == old_name:
                w.action.name = new_name
                break

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        row = self._list.row(item)
        widget = self._item_widget(row)
        if widget is None:
            return

        menu = QMenu(self)
        is_editing = self._app_state == AppState.EDITING
        remove_action = menu.addAction("Remove")
        remove_action.setEnabled(is_editing)
        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.setEnabled(is_editing)

        chosen = menu.exec(self._list.mapToGlobal(pos))

        if chosen == remove_action:
            self._remove_action(row, widget.action)
        elif chosen == duplicate_action:
            self._duplicate_action(widget.action)

    def _remove_action(self, row: int, action: Action) -> None:
        self._list.takeItem(row)
        self._manager.workflow.actions.remove(action)
        self._manager.notify_workflow_changed()

    def _duplicate_action(self, action: Action) -> None:
        new_name = self._generate_unique_name(action.name)
        type_key = next(
            key for key in ACTION_REGISTRY if ACTION_REGISTRY.get(key) is type(action)
        )
        new_action = self._build_action(type_key, new_name)
        self._manager.workflow.actions.append(new_action)
        self._append_item(new_action)
        self._manager.notify_workflow_changed()

    def on_app_state_changed(self, state: AppState) -> None:
        """Called by MainWindow when the application state changes."""
        self._app_state = state
        is_editing = state == AppState.EDITING
        self._add_btn.setEnabled(is_editing)

        self._list.setDragDropMode(
            QAbstractItemView.DragDropMode.InternalMove
            if is_editing
            else QAbstractItemView.DragDropMode.NoDragDrop
        )

    def set_action_state(self, action_name: str, state: str) -> None:
        """
        Update the state dot for the given action.

        Args:
            action_name: Name of the action to update.
            state: One of 'idle', 'running', 'completed', 'failed'.
        """
        for i in range(self._list.count()):
            w = self._item_widget(i)
            if w is not None and w.action.name == action_name:
                w.set_state(state)
                break

    def refresh_propagation_badges(self) -> None:
        """Refresh all propagation badges, e.g. after rules are added or removed."""
        for i in range(self._list.count()):
            w = self._item_widget(i)
            if w is not None:
                w.update_propagation_badge()
