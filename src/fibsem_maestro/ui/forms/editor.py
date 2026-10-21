# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The contract every field editor implements."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

    from fibsem_maestro.ui.forms.issues import FieldIssue

OnChange = Callable[[], None]
"""A callback fired when an editor's value (or issues) changed."""


def noop() -> None:
    """A do-nothing `OnChange`."""


T = TypeVar("T")


# not an ABC: combined with QWidget subclasses, ABCMeta conflicts with sip's metaclass
class FieldEditor(Generic[T]):
    """
    Interface of a field editor, mixed into a `QWidget` subclass.

    Provides change notification, holds the issues reported on the field, and
    defines the value, read-only and structure accessors. Parameterised by the
    type `T` of the editor's value.
    """

    def __init__(self) -> None:
        self._change_hooks: list[OnChange] = []
        self._issues: dict[str, FieldIssue] = {}
        self._issue_hooks: list[OnChange] = []

    def on_change(self, hook: OnChange) -> None:
        """
        Register a callback fired when this editor's own value changes.

        Args:
            hook: The callback.
        """
        self._change_hooks.append(hook)

    def _emit(self) -> None:
        """Fire this editor's change callbacks."""
        for hook in self._change_hooks:
            hook()

    def get_value(self) -> T:
        """
        Return the editor's current value.

        Returns:
            The current value.

        Raises:
            FieldValidationError: If no valid value can be built from the editor.
            NotImplementedError: If the subclass does not override this method.
        """
        raise NotImplementedError(
            f"get_value not implemented for {type(self).__name__}"
        )

    def set_value(self, value: T) -> None:
        """
        Show a value.

        Args:
            value: The new value.

        Raises:
            NotImplementedError: If the subclass does not override this method.
        """
        raise NotImplementedError(
            f"set_value not implemented for {type(self).__name__}"
        )

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable editing.

        Args:
            read_only: If True, the editor prevents user edits.

        Raises:
            NotImplementedError: If the subclass does not override this method.
        """
        raise NotImplementedError(
            f"set_read_only not implemented for {type(self).__name__}"
        )

    def highlight_target(self) -> QWidget:
        """
        Return the widget a paired `FieldLabel` highlights on hover.

        Defaults to this editor. Wrappers gating a single inner editor (e.g.
        `OptionalWidget`) return that editor, so the highlight hugs the
        control instead of the full-width wrapper.

        Returns:
            The widget receiving the `highlighted` property on hover.
        """
        return cast("QWidget", self)

    def set_issue(self, source: str, issue: FieldIssue | None) -> None:
        """
        Attach, replace or clear the issue one producer reports on this field.

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
        """
        Register a callback fired when the issues reported on this field change.

        Args:
            hook: The callback.
        """
        self._issue_hooks.append(hook)

    def _emit_issues_changed(self) -> None:
        """Fire this editor's issue callbacks."""
        for hook in self._issue_hooks:
            hook()

    def value_editor(self) -> FieldEditor[Any]:
        """
        Return the editor holding the value.

        Returns:
            This editor, or for a wrapper (optional checkbox, group box) the
            value editor of the wrapped editor.
        """
        return self

    def child_editors(self, name: str, all_variants: bool) -> list[FieldEditor[Any]]:
        """
        Return the editors of the field `name` inside this editor.

        Args:
            name: The field name.
            all_variants: For a union editor, look in every variant instead of
                only the selected one.

        Returns:
            The matching editors, each reduced to its `value_editor()`. Empty
            for editors without named fields (the default).
        """
        _ = name, all_variants
        return []
