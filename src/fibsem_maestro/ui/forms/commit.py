# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Writes a field of a live object from its editor, after validating it."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from pydantic import ValidationError
from PyQt6.QtWidgets import QWidget

from fibsem_maestro.ui.forms.editor import FieldEditor
from fibsem_maestro.ui.forms.issues import (
    VALIDATION_ISSUE,
    FieldIssue,
    FieldValidationError,
    Severity,
)
from fibsem_maestro.ui.forms.scope import ObjectPath, resolve_path
from fibsem_maestro.ui.schema.validation import (
    validate_assignment,
    validation_messages,
)

if TYPE_CHECKING:
    from fibsem_maestro.ui.forms.scope import BuildContext
    from fibsem_maestro.ui.schema.field_info import FieldInfo

_NESTED_PROBLEM = "Contains an invalid value."
"""Shown on the field itself when its problems lie in nested fields, which may be collapsed."""


class FieldCommitter:
    """
    The commit path of one field of a live object.

    Used as the `on_change` of the field's editor and threaded through the
    editor's subtree. On any change it validates the editor's current value as
    the owner would on assignment, then assigns the whole field. An invalid
    value is not written, so the field keeps its last valid value; instead,
    every editor at fault shows an error until a later edit makes the value
    valid again.

    The owner is looked up from the root on every call, so an owner replaced
    in the settings (e.g. by unticking and ticking an optional group) receives
    later edits. While the owner is None, the committer does nothing.

    Once the form is disposed, the committer does nothing at all.

    The editor is bound after its subtree is built, since the committer must
    already exist while the subtree is constructed.

    Args:
        root: The form's live root object.
        owner: Path from `root` to the object owning the field.
        fi: The field.
        context: The form's build. Its `on_commit` is called with the field's
            dotted path from the root after every successful assignment; its
            form's `log` receives faults that are not validation failures.
    """

    def __init__(
        self,
        root: Any,
        owner: ObjectPath,
        fi: FieldInfo,
        context: BuildContext,
    ) -> None:
        self._root = root
        self._owner = owner
        self._fi = fi
        self._context = context
        self._editor: FieldEditor[Any] | None = None

    @property
    def dotted_path(self) -> str:
        """The field's dotted path from the form root."""
        return ".".join((*self._owner, self._fi.name))

    def bind(self, editor: FieldEditor[Any]) -> None:
        """
        Attach the field editor this committer reads from.

        Args:
            editor: The field's (outermost) editor.
        """
        self._editor = editor

    def __call__(self) -> None:
        if self._context.disposed:
            return
        owner = resolve_path(self._root, self._owner)
        if self._editor is None or owner is None:
            return

        valid, value = self._read_validated(owner, self._editor)
        if not valid:
            return

        setattr(owner, self._fi.name, value)
        # exactly one write per edit, so the side effect also happens once
        self._context.on_commit(self.dotted_path)

    def check(self) -> None:
        """
        Validate the field's current form value and show the result, without writing it.

        Run once the form is built, so a stored value the form cannot show
        (e.g. a link to an action that is not in the workflow) is marked
        before any edit. Does nothing once the form is disposed.
        """
        if self._context.disposed:
            return
        owner = resolve_path(self._root, self._owner)
        if self._editor is not None and owner is not None:
            self._read_validated(owner, self._editor)

    def _read_validated(self, owner: Any, editor: FieldEditor[Any]) -> tuple[bool, Any]:
        """
        Read and validate the editor's value, showing any errors on the form.

        Args:
            owner: The object owning the field.
            editor: The bound field editor.

        Returns:
            `(True, value)` with the validated value, or `(False, None)` if the value is invalid.
        """
        try:
            # validated as the owner would on assignment, which pydantic owners
            # do not do themselves
            value = validate_assignment(owner, self._fi.name, editor.get_value())
        except FieldValidationError as e:
            self._report(editor, e.attributed_to(editor))
            return False, None
        except ValidationError as e:
            self._report(editor, [(editor, m) for m in validation_messages(e)])
            return False, None
        except Exception as e:
            # not a validation failure but a fault while reading the form: keep the trace
            if (log := self._context.form.log) is not None:
                log.error(f"Reading field '{self._fi.name}' failed: {e!r}")
            self._report(editor, [(editor, str(e))])
            return False, None

        self._report(editor, [])
        return True, value

    def _report(
        self, editor: FieldEditor[Any], problems: list[tuple[FieldEditor[Any], str]]
    ) -> None:
        """
        Replace this field's validation errors with `problems`.

        Every editor of the field's subtree is updated, including pages of
        union variants not currently selected, so errors left from an earlier
        edit are cleared. If all problems lie in nested fields, the field
        itself also shows a short note, since nested groups may be collapsed.

        Args:
            editor: The bound field editor.
            problems: `(editor at fault, message)` pairs; empty if the value is valid.
        """
        errors: dict[int, tuple[FieldEditor[Any], list[str]]] = {}
        for at_fault, message in problems:
            messages = errors.setdefault(id(at_fault), (at_fault, []))[1]
            if message not in messages:
                messages.append(message)

        if errors and id(editor) not in errors:
            errors[id(editor)] = (editor, [_NESTED_PROBLEM])

        subtree = [editor] + [
            child
            for child in cast("QWidget", editor).findChildren(QWidget)
            if isinstance(child, FieldEditor)
        ]

        for target in subtree:
            entry = errors.pop(id(target), None)
            target.set_issue(
                VALIDATION_ISSUE,
                FieldIssue(Severity.ERROR, "\n".join(entry[1])) if entry else None,
            )

        # editors outside the subtree are not expected, but must not lose their error
        for target, messages in errors.values():
            target.set_issue(
                VALIDATION_ISSUE, FieldIssue(Severity.ERROR, "\n".join(messages))
            )
