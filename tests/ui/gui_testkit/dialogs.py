# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Stand-ins for everything that would block a test or end the process."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from PyQt6.QtWidgets import QMessageBox

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class ExitCalls:
    """The `os._exit` calls a test made; none of them ends the process."""

    codes: list[int] = field(default_factory=list)


@dataclass
class MessageBoxes:
    """
    Stand-in for the static `QMessageBox` functions.

    Attributes:
        calls: `(kind, title, text)` of every box shown; kind is "warning",
            "critical", "information" or "question".
        answer: What every box returns (e.g. Yes or Cancel for a question).
    """

    calls: list[tuple[str, str, str]] = field(default_factory=list)
    answer: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes

    def titles(self) -> list[str]:
        """The titles of the boxes shown, in order."""
        return [title for _, title, _ in self.calls]

    def texts(self) -> list[str]:
        """The texts of the boxes shown, in order."""
        return [text for _, _, text in self.calls]

    def recorder(self, kind: str) -> Callable[..., Any]:
        """
        A replacement for one static `QMessageBox` function.

        Args:
            kind: The function's name.

        Returns:
            A function recording its call and returning `answer`.
        """

        def show(
            _parent: object, title: str, text: str, *_: object, **__: object
        ) -> Any:
            self.calls.append((kind, title, text))
            return self.answer

        return show


@dataclass
class DirectoryChoices:
    """
    Stand-in for `QFileDialog.getExistingDirectory`.

    Attributes:
        path: What the dialog returns; "" means the user cancelled.
        titles: Titles of the dialogs shown, in order.
    """

    path: str = ""
    titles: list[str] = field(default_factory=list)

    def choose(
        self, _parent: object = None, title: str = "", *_: object, **__: object
    ) -> str:
        """Record the dialog and return `path`."""
        self.titles.append(title)
        return self.path
