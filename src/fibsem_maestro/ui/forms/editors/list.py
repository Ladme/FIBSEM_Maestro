# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Editor of a list: one item editor per element, with add and remove buttons."""

from collections.abc import Callable
from typing import TypeVar, cast

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.ui.forms.editor import FieldEditor

T = TypeVar("T")


class ListWidget(QWidget, FieldEditor[list[T]]):
    """
    A vertical list of same-type widgets with add and remove controls.

    Args:
        item_factory: Callable that returns a new FieldEditor for each item.
        default: Initial list of values to pre-populate.
        parent: Parent widget.
    """

    def __init__(
        self,
        item_factory: Callable[[], FieldEditor[T]],
        default: list[T] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        FieldEditor.__init__(self)
        self._item_factory = item_factory
        self._items: list[FieldEditor[T]] = []
        self._remove_buttons: dict[int, QPushButton] = {}
        self._read_only = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._group = QGroupBox()
        group_layout = QVBoxLayout(self._group)
        group_layout.setSpacing(4)

        self._items_layout = QVBoxLayout()
        self._items_layout.setSpacing(4)
        group_layout.addLayout(self._items_layout)

        self._add_btn = QPushButton("+")
        self._add_btn.setFixedSize(22, 22)
        self._add_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._add_btn.clicked.connect(self._add_item)
        group_layout.addWidget(self._add_btn)

        outer.addWidget(self._group)

        for value in default or []:
            self._add_item(value)

    def _add_item(self, value: T | None = None) -> None:
        """
        Append an item, removable on its own, and notify a change.

        Args:
            value: The new item's value; None for the item editor's default.
        """
        widget = self._item_factory()

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(cast("QWidget", widget))
        cast("QWidget", widget).setSizePolicy(
            QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed
        )

        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(22, 22)
        remove_btn.clicked.connect(lambda: self._remove_item(row, widget))
        row.addWidget(remove_btn)
        row.addStretch()

        self._items_layout.addLayout(row)
        self._items.append(widget)
        self._remove_buttons[id(widget)] = remove_btn

        if value is not None:
            widget.set_value(value)
        if self._read_only:
            widget.set_read_only(True)
            remove_btn.setEnabled(False)

        self._emit()

    def _remove_item(self, row: QHBoxLayout, widget: FieldEditor[T]) -> None:
        """
        Remove an item widget and its row, then notify listeners.

        Args:
            row: The row layout holding the widget and its remove button.
            widget: The item widget to remove.
        """

        self._items.remove(widget)
        self._remove_buttons.pop(id(widget), None)

        while row.count():
            item = row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._items_layout.removeItem(row)
        self._emit()

    def get_value(self) -> list[T]:
        """
        Return the values of all items in order.

        Returns:
            A list of the current item values.
        """

        return [w.get_value() for w in self._items]

    def set_value(self, value: list[T] | None) -> None:
        """
        Show exactly one item per value, in order.

        Args:
            value: The values to show; None shows an empty list.
        """
        while self._items:
            item = self._items[0]
            row = self._items_layout.itemAt(0)
            if row:
                self._remove_item(cast("QHBoxLayout", row.layout()), item)
        for v in value or []:
            self._add_item(v)

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable editing of the whole list.

        Args:
            read_only: If True, prevent edits and block adding or removing items.
        """
        self._read_only = read_only

        self._add_btn.setEnabled(not read_only)
        for w in self._items:
            w.set_read_only(read_only)
        for btn in self._remove_buttons.values():
            btn.setEnabled(not read_only)
