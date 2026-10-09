# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from typing import Any, cast

from pydantic import ValidationError
from PyQt6.QtWidgets import QWidget

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.form_builder.issues import (
    VALIDATION_ISSUE,
    FieldIssue,
    FieldValidationError,
    Severity,
    validation_messages,
)
from fibsem_maestro.gui.form_builder.schema.field_info import FieldInfo
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.workflow_manager import WorkflowManager
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.settings.base_settings import BaseSettings

_NESTED_PROBLEM = "Contains an invalid value."
"""Shown on the field itself when its problems lie in nested fields, which may be collapsed."""


class WriteBack:
    """
    The single write-back for one top-level field.

    Threaded through the field's subtree as `on_change`. On any change it
    validates the field widget's current value as the settings class would on
    assignment, then reassigns the whole field on the reactive root. An
    invalid value is not written (whole-unit validation), so the field keeps
    its last valid value; instead, every widget at fault shows an error until
    a later edit makes the value valid again.

    The widget is bound after the subtree is built, since the callback must
    already exist while the subtree (and its dynamic children) is constructed.
    """

    def __init__(
        self,
        settings: BaseSettings,
        fi: FieldInfo,
        manager: WorkflowManager | None,
        action: Action | None,
        txt_log: TextLogger,
    ) -> None:
        self._settings = settings
        self._fi = fi
        self._manager = manager
        self._action = action
        self._widget: BaseWidget | None = None
        self._txt_log = txt_log
        self._failed = False

    def bind(self, widget: BaseWidget) -> None:
        """Attach the field widget this write-back reads from."""
        self._widget = widget

    def __call__(self) -> None:
        if self._widget is None:
            return

        widget = self._widget

        try:
            value = self._validated(widget.get_value())
        except FieldValidationError as e:
            self._report(widget, e.attributed_to(widget))
            return
        except ValidationError as e:
            self._report(widget, [(widget, m) for m in validation_messages(e)])
            return
        except Exception as e:
            # not a validation failure but a fault while reading the form: keep the trace
            self._txt_log.error(f"Reading field '{self._fi.name}' failed: {e!r}")
            self._report(widget, [(widget, str(e))])
            return

        setattr(self._settings, self._fi.name, value)
        self._report(widget, [])

        # exactly one write per edit, so the side effect also fires once
        if self._action is not None and self._manager is not None:
            self._manager.action_changed.emit(self._action)

    def _validated(self, value: Any) -> Any:
        """
        Validate a new value for this field as the settings class would on assignment.

        The settings do not validate assignments, so without this the
        constraints and validators of top-level fields would never run, and an
        invalid value would be stored and only fail when the settings file is
        loaded again. Validation runs on a shallow copy, so the live settings
        and their hooks are untouched.

        Args:
            value: The value read from the field widget.

        Returns:
            The validated value, possibly coerced (e.g. a list rebuilt).

        Raises:
            pydantic.ValidationError: If the value is invalid for this field.
        """
        probe = self._settings.model_copy()
        type(self._settings).__pydantic_validator__.validate_assignment(
            probe, self._fi.name, value
        )

        return getattr(probe, self._fi.name)

    def _report(
        self, widget: BaseWidget, problems: list[tuple[BaseWidget, str]]
    ) -> None:
        """
        Replace this field's validation errors with `problems`.

        Every widget of the field's subtree is updated, including pages of
        union variants not currently selected, so errors left from an earlier
        edit are cleared. If all problems lie in nested fields, the field
        itself also shows a short note, since nested groups may be collapsed.
        Notifies the manager when the field turns valid or invalid.

        Args:
            widget: The bound field widget.
            problems: `(widget at fault, message)` pairs; empty if the value is valid.
        """
        errors: dict[int, tuple[BaseWidget, list[str]]] = {}
        for at_fault, message in problems:
            messages = errors.setdefault(id(at_fault), (at_fault, []))[1]
            if message not in messages:
                messages.append(message)

        if errors and id(widget) not in errors:
            errors[id(widget)] = (widget, [_NESTED_PROBLEM])

        subtree = [widget] + [
            child
            for child in cast("QWidget", widget).findChildren(QWidget)
            if isinstance(child, BaseWidget)
        ]

        for target in subtree:
            entry = errors.pop(id(target), None)
            target.set_issue(
                VALIDATION_ISSUE,
                FieldIssue(Severity.ERROR, "\n".join(entry[1])) if entry else None,
            )

        # widgets outside the subtree are not expected, but must not lose their error
        for target, messages in errors.values():
            target.set_issue(
                VALIDATION_ISSUE, FieldIssue(Severity.ERROR, "\n".join(messages))
            )

        failed = bool(problems)
        if failed != self._failed:
            self._failed = failed
            if self._manager is not None:
                self._manager.notify_form_issues_changed()
