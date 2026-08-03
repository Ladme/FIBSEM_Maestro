# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from collections.abc import Callable
from typing import Any

from PyQt6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.gui.common import class_name_to_label
from fibsem_maestro.gui.form_builder.schema.field_info import FieldInfo
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.form_builder.widgets.object import ObjectWidget


def _get_field_infos_for_variant(cls: type):
    """
    Return the field infos for a variant class.

    Args:
        cls: The variant class to introspect.

    Returns:
        The field infos describing the class's fields.
    """

    # import get_field_infos locally to avoid circular imports
    from fibsem_maestro.gui.form_builder.schema.schema import get_field_infos

    return get_field_infos(cls)


class DiscriminatedUnionWidget(QWidget, BaseWidget[Any]):
    """
    Radio buttons + QStackedWidget for discriminated unions.
    One radio button per variant. Selecting a variant shows its extra fields
    (fields beyond the discriminator key) in a QStackedWidget below.
    Variants with no extra fields show nothing below the radio buttons.

    Args:
        variants: The (discriminator value, variant class) pairs to offer.
        discriminator_key: The field name whose value identifies the variant.
        build_object: Factory that builds an ObjectWidget for a variant class from a list of field infos.
        parent: The parent widget, if any.
    """

    def __init__(
        self,
        variants: list[tuple[str, type]],
        discriminator_key: str,
        build_object: Callable[[type, list[FieldInfo] | None], ObjectWidget[Any]],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        BaseWidget.__init__(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._discriminator_key = discriminator_key
        self._discriminator_values: list[str] = []
        self._variant_classes: list[type] = []
        self._empty_indices: set[int] = set()
        self._variant_widgets: list[QWidget] = []

        self._button_group = QButtonGroup(self)
        radio_row = QHBoxLayout()

        for i, (disc_value, variant_cls) in enumerate(variants):
            self._discriminator_values.append(disc_value)
            self._variant_classes.append(variant_cls)

            btn = QRadioButton(class_name_to_label(variant_cls.__name__))
            self._button_group.addButton(btn, i)
            radio_row.addWidget(btn)

            extra_field_infos = [
                fi
                for fi in _get_field_infos_for_variant(variant_cls)
                if fi.name != discriminator_key
            ]

            if extra_field_infos:
                variant_widget = build_object(variant_cls, extra_field_infos)
            else:
                variant_widget = QWidget()
                self._empty_indices.add(i)

            self._variant_widgets.append(variant_widget)
            layout.addWidget(variant_widget)
            variant_widget.hide()

        # radio buttons on top, variant widgets below
        layout.insertLayout(0, radio_row)

        first_btn = self._button_group.button(0)
        if first_btn:
            first_btn.setChecked(True)
            self._on_selection_changed(0)

        self._button_group.idClicked.connect(self._on_selection_changed)

    def _on_selection_changed(self, index: int) -> None:
        """
        Show the selected variant's fields, hide the rest, then notify.

        Called when the selected variant changes.

        Args:
            index: The index of the newly selected variant.
        """

        for i, widget in enumerate(self._variant_widgets):
            widget.setVisible(i == index and index not in self._empty_indices)
        self._emit()

    def get_value(self) -> Any:
        """
        Construct the selected variant instance from its fields.

        Returns:
            An instance of the currently selected variant class.
        """

        index = self._button_group.checkedId()
        variant_cls = self._variant_classes[index]
        data = {self._discriminator_key: self._discriminator_values[index]}

        if index not in self._empty_indices:
            widget = self._variant_widgets[index]
            if isinstance(widget, ObjectWidget):
                data.update(widget.values_dict())

        return variant_cls(**data)

    def set_value(self, value: Any) -> None:
        """
        Select and populate the variant matching a value's discriminator.

        Args:
            value: The variant instance to display.
        """

        disc_value = getattr(value, self._discriminator_key, None)
        if disc_value not in self._discriminator_values:
            return

        index = self._discriminator_values.index(disc_value)
        if index not in self._empty_indices:
            widget = self._variant_widgets[index]
            if isinstance(widget, BaseWidget):
                widget.set_value(value)

        btn = self._button_group.button(index)
        if btn:
            btn.setChecked(True)
        self._on_selection_changed(index)

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable the radio buttons and all variant widgets.

        Args:
            read_only: If True, prevent variant selection and edits.
        """
        # disable radio buttons
        for btn in self._button_group.buttons():
            btn.setEnabled(not read_only)

        # propagate to all variant widgets
        for widget in self._variant_widgets:
            if isinstance(widget, BaseWidget):
                widget.set_read_only(read_only)
