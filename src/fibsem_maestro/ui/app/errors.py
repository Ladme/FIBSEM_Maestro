# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Errors raised by the application layer; the views translate them into message boxes."""

from pathlib import Path


class NotAllowedError(Exception):
    """A command was refused because the current state does not allow it."""


class InvalidActionNameError(ValueError):
    """A proposed action name is empty, taken or reserved; the message says which."""


class ActionRenameError(Exception):
    """Moving an action's directory failed; nothing was changed. Chained to the OSError."""


class DirectoryNotClearedError(Exception):
    """
    Some children of a directory could not be deleted.

    Args:
        failures: Each path that could not be deleted, with its error.
    """

    def __init__(self, failures: list[tuple[Path, OSError]]) -> None:
        super().__init__(
            "\n".join(f"- {path.name}: {error}" for path, error in failures)
        )
        self.failures = failures


class WorkflowImportError(Exception):
    """Importing a workflow failed. Chained to the cause; the message is the cause's."""


class WorkflowResetError(Exception):
    """Resetting the workflow failed. Chained to the cause; the message is the cause's."""
