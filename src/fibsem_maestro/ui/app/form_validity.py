# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Which actions' settings forms currently show an error."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from fibsem_maestro.action.action import Action


class FormValidity(QObject):
    """
    Which actions' settings forms currently show an error (only open forms can).

    Each form reports its own state; a value a form rejected never reached the
    settings, so readiness must know about it.

    Args:
        parent: Optional Qt parent.
    """

    changed = pyqtSignal()
    """The set of owners with errors changed."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._owners: set[Action] = set()

    def set_has_errors(self, owner: Action, has_errors: bool) -> None:
        """
        Record whether the owner's form shows an error; emits `changed` only on change.

        Args:
            owner: The action whose settings form reports.
            has_errors: True if some field of the form shows an error.
        """
        if has_errors == (owner in self._owners):
            return
        if has_errors:
            self._owners.add(owner)
        else:
            self._owners.discard(owner)
        self.changed.emit()

    def forget(self, owner: Action) -> None:
        """
        Drop the owner, whose form was discarded.

        Args:
            owner: The action whose panel was discarded.
        """
        self.set_has_errors(owner, False)

    def owners_with_errors(self) -> frozenset[Action]:
        """The actions whose forms currently show an error."""
        return frozenset(self._owners)
