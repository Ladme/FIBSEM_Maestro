# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, TypeVar, cast

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

    from fibsem_maestro.gui.form_builder.issues import FieldIssue

OnChange = Callable[[], None]


def _noop() -> None:
    """A do-nothing default `on_change`."""


T = TypeVar("T")


# this cannot be ABC due to some metaclass conflicts
class BaseWidget(Generic[T]):
    """
    Base interface for field widgets.

    Provides a change-notification mechanism, holds the issues reported on
    the field, and defines the value and read-only accessors that concrete
    widgets must implement.

    Parameterized by the type `T` of the widget's value.
    """

    def __init__(self) -> None:
        self._change_hooks: list[OnChange] = []
        self._issues: dict[str, FieldIssue] = {}
        self._issue_hooks: list[OnChange] = []

    def on_change(self, hook: OnChange) -> None:
        """Register a callback fired when this widget's own state changes."""
        self._change_hooks.append(hook)

    def _emit(self) -> None:
        """Fire this widget's callbacks."""
        for hook in self._change_hooks:
            hook()

    def get_value(self) -> T:
        """
        Return the widget's current value.

        Returns:
            The current value of type `T`.

        Raises:
            NotImplementedError: If the subclass does not override this method.
        """

        raise NotImplementedError(
            f"get_value not implemented for {type(self).__name__}"
        )

    def set_value(self, value: T) -> None:
        """
        Set the widget's value.

        Args:
            value: The new value of type `T`.

        Raises:
            NotImplementedError: If the subclass does not override this method.
        """
        raise NotImplementedError(
            f"set_value not implemented for {type(self).__name__}"
        )

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable read-only mode for the widget.

        Args:
            read_only: If True, the widget should prevent user edits.

        Raises:
            NotImplementedError: If the subclass does not override this method.
        """
        raise NotImplementedError(
            f"set_read_only not implemented for {type(self).__name__}"
        )

    def highlight_target(self) -> QWidget:
        """
        Return the widget a paired `FieldLabel` should highlight on hover.

        Defaults to this widget. Wrappers that gate a single inner editor
        (e.g. `OptionalWidget`) override this to point at that editor, so the
        highlight hugs the control instead of the full-width wrapper.

        Returns:
            The widget to receive the `highlighted` property on hover.
        """
        return cast("QWidget", self)

    def set_issue(self, source: str, issue: FieldIssue | None) -> None:
        """
        Attach, replace, or clear the issue one producer reports on this field.

        Args:
            source: Key of the producer, e.g. `VALIDATION_ISSUE`; each producer
                replaces only its own issue.
            issue: The issue, or None to clear it.
        """
        if self._issues.get(source) == issue:
            return

        if issue is None:
            del self._issues[source]
        else:
            self._issues[source] = issue

        self._emit_issues_changed()

    def issues(self) -> list[FieldIssue]:
        """
        Return the issues currently reported on this field.

        Returns:
            One issue per reporting producer.
        """
        return list(self._issues.values())

    def on_issues_changed(self, hook: OnChange) -> None:
        """Register a callback fired when the issues reported on this field change."""
        self._issue_hooks.append(hook)

    def _emit_issues_changed(self) -> None:
        """Fire this widget's issue callbacks."""
        for hook in self._issue_hooks:
            hook()
