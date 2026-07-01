# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from typing import Any, cast

from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class ListWidget(QWidget, WidgetWrapper):
    """
    A vertical list of same-type widgets with add and remove controls.

    Args:
        item_factory: Callable that returns a new WidgetWrapper for each item.
        default: Initial list of values to pre-populate.
        parent: Parent widget.
    """

    def __init__(
        self,
        item_factory: Callable[[], WidgetWrapper],
        default: list[Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        WidgetWrapper.__init__(self)
        self._item_factory = item_factory
        self._items: list[WidgetWrapper] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._group = QGroupBox()
        group_layout = QVBoxLayout(self._group)
        group_layout.setSpacing(4)

        self._items_layout = QVBoxLayout()
        self._items_layout.setSpacing(4)
        group_layout.addLayout(self._items_layout)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(22, 22)
        add_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        add_btn.clicked.connect(self._add_item)
        group_layout.addWidget(add_btn)

        outer.addWidget(self._group)

        for value in default or []:
            self._add_item(value)

    def _add_item(self, value: Any = None) -> None:
        widget = self._item_factory()
        widget._parent = self

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

        if value is not None:
            widget.set_value(value)
        self._notify_changed()

    def _remove_item(self, row: QHBoxLayout, widget: WidgetWrapper) -> None:
        self._items.remove(widget)
        while row.count():
            item = row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._items_layout.removeItem(row)
        self._notify_changed()

    def get_value(self) -> list[Any]:
        return [w.get_value() for w in self._items]

    def set_value(self, value: Any) -> None:
        while self._items:
            item = self._items[0]
            row = self._items_layout.itemAt(0)
            if row:
                self._remove_item(cast("QHBoxLayout", row.layout()), item)
        for v in value or []:
            self._add_item(v)

    def set_read_only(self, read_only: bool) -> None:
        for w in self._items:
            w.set_read_only(read_only)
