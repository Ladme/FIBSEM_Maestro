# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from PyQt6.QtWidgets import QCheckBox, QWidget

from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget


class BoolWidget(QCheckBox, BaseWidget[bool]):
    """
    A checkbox widget for editing a boolean value.

    Args:
        default: The initial checked state.
        parent: The parent widget, if any.
    """

    def __init__(self, default: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        BaseWidget.__init__(self)
        self.setChecked(bool(default))
        self.toggled.connect(lambda _: self._emit())

    def get_value(self) -> bool:
        """
        Return whether the checkbox is checked.

        Returns:
            True if checked, False otherwise.
        """

        return self.isChecked()

    def set_value(self, value: bool) -> None:
        """
        Set the checkbox's checked state.

        Args:
            value: The new checked state.
        """

        self.setChecked(bool(value))

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable user interaction with the widget.

        Args:
            read_only: If True, disable the widget to prevent changes.
        """
        self.setEnabled(not read_only)
