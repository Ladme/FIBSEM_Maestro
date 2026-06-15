# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.action_list_panel._common import STATE_COLORS
from fibsem_maestro.gui.common import class_name_to_label
from fibsem_maestro.workflow.propagations import Propagations


class ActionItemWidget(QWidget):
    """
    Widget displayed inside each list item.

    Shows a state dot, action name, action type, and propagation badge.
    The name is editable by double-clicking.

    Args:
        action: The action this item represents.
        propagations: The propagations manager, used to count outgoing rules.
    """

    name_changed = pyqtSignal(str, str)  # old_name, new_name

    def __init__(
        self,
        action: Action,
        propagations: Propagations,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._action = action
        self._propagations = propagations
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        # state dot
        self._dot = QLabel("●")
        self._dot.setFixedWidth(12)
        self._dot.setStyleSheet(f"color: {STATE_COLORS['idle']}; font-size: 8px;")
        layout.addWidget(self._dot)

        # vertical group: name row + subtitle
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        # name row: name label + propagation badge
        name_row = QHBoxLayout()
        name_row.setContentsMargins(0, 0, 0, 0)
        name_row.setSpacing(6)

        # name label (double-click to edit)
        self._name_label = QLabel(action.name)
        self._name_label.setStyleSheet("font-weight: bold;")
        self._name_label.mouseDoubleClickEvent = self._start_name_edit
        name_row.addWidget(self._name_label)

        # inline name editor (hidden by default)
        self._name_edit = QLineEdit(action.name)
        self._name_edit.hide()
        self._name_edit.returnPressed.connect(self._finish_name_edit)
        self._name_edit.editingFinished.connect(self._finish_name_edit)
        name_row.addWidget(self._name_edit)

        # propagation badge
        self._badge = QLabel()
        self._badge.setStyleSheet("color: #5a9fd4; font-size: 11px;")
        name_row.addWidget(self._badge)

        name_row.addStretch()
        text_layout.addLayout(name_row)

        # type + beam subtitle
        subtitle_label = QLabel(
            f"{class_name_to_label(type(action).__name__)}  ·  {action.beam_type if action.beam_type is not None else '—'}"
        )
        subtitle_label.setStyleSheet("color: #888888; font-size: 10px;")
        text_layout.addWidget(subtitle_label)

        layout.addLayout(text_layout)
        self.update_propagation_badge()

    def _start_name_edit(self, event) -> None:
        _ = event
        self._name_label.hide()
        self._name_edit.setText(self._name_label.text())
        self._name_edit.show()
        self._name_edit.setFocus()
        self._name_edit.selectAll()

    def _finish_name_edit(self) -> None:
        new_name = self._name_edit.text().strip()
        if new_name and new_name != self._name_label.text():
            old_name = self._name_label.text()
            self._name_label.setText(new_name)
            self.name_changed.emit(old_name, new_name)
        self._name_edit.hide()
        self._name_label.show()

    def update_propagation_badge(self) -> None:
        """Recount outgoing propagation rules and update the badge."""
        count = sum(
            1
            for rule in self._propagations.rules
            if rule.parent_name == self._action.name
        )
        if count > 0:
            dependents = ", ".join(
                d
                for rule in self._propagations.rules
                if rule.parent_name == self._action
                for d in rule.dependent_names
            )
            self._badge.setText(f"→{count}")
            self._badge.setToolTip(f"Propagates to: {dependents}")
        else:
            self._badge.setText("")
            self._badge.setToolTip("")

    def set_state(self, state: str) -> None:
        """Update the state dot color. State is one of: idle/running/completed/failed."""
        color = STATE_COLORS.get(state, STATE_COLORS["idle"])
        self._dot.setStyleSheet(f"color: {color}; font-size: 8px;")

    @property
    def action(self) -> Action:
        return self._action
