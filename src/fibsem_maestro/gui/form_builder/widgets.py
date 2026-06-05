# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

import json
from enum import Enum
from typing import TYPE_CHECKING, Any, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.gui.form_builder.utils import FieldInfo, class_name_to_label

if TYPE_CHECKING:
    from collections.abc import Callable

GROUP_BOX_COLORS = [
    "#2d4a5a",
    "#2d5a4a",
    "#4a2d5a",
    "#5a4a2d",
]


class FieldLabel(QLabel):
    """A label that highlights its paired input widget on hover."""

    def __init__(
        self,
        text: str,
        paired_widget: QWidget,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._paired = paired_widget

    def enterEvent(self, event) -> None:
        self._paired.setProperty("highlighted", True)
        self._refresh_style(self._paired)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._paired.setProperty("highlighted", False)
        self._refresh_style(self._paired)
        super().leaveEvent(event)

    @staticmethod
    def _refresh_style(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()


class WidgetWrapper:
    """
    Base interface for field widgets.
    """

    def get_value(self) -> Any:
        raise NotImplementedError(
            f"get_value is not implemented for {self.__class__.__name__}"
        )

    def set_value(self, value: Any) -> None:
        raise NotImplementedError(
            f"set_value is not implemented for {self.__class__.__name__}"
        )


class StringWidget(QWidget, WidgetWrapper):
    def __init__(
        self,
        default: str = "",
        suffix: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._edit = QLineEdit()
        self._edit.setText(str(default) if default else "")
        layout.addWidget(self._edit)

        if suffix:
            layout.addWidget(QLabel(suffix))

    def get_value(self) -> str | None:
        text = self._edit.text()
        return text if text != "" else None

    def set_value(self, value: str | None) -> None:
        self._edit.setText(str(value) if value is not None else "")


class IntWidget(QWidget, WidgetWrapper):
    def __init__(
        self,
        default: int = 0,
        minimum: float | None = None,
        maximum: float | None = None,
        suffix: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._spin = QSpinBox()
        # use large sentinels for 'no limit'
        self._spin.setMinimum(int(minimum) if minimum is not None else -2_147_483_648)
        self._spin.setMaximum(int(maximum) if maximum is not None else 2_147_483_647)
        self._spin.setValue(int(default))
        layout.addWidget(self._spin)

        if suffix:
            layout.addWidget(QLabel(suffix))

    def get_value(self) -> int:
        return self._spin.value()

    def set_value(self, value: Any) -> None:
        self._spin.setValue(int(value))


class FloatWidget(QWidget, WidgetWrapper):
    """Floating-point spinner for JSON 'float' fields."""

    def __init__(
        self,
        default: float = 0.0,
        minimum: float | None = None,
        maximum: float | None = None,
        suffix: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._spin = QDoubleSpinBox()
        self._spin.setDecimals(6)
        self._spin.setMinimum(minimum if minimum is not None else -1e12)
        self._spin.setMaximum(maximum if maximum is not None else 1e12)
        self._spin.setSingleStep(0.1)
        self._spin.setValue(float(default))
        layout.addWidget(self._spin)

        if suffix:
            layout.addWidget(QLabel(suffix))

    def get_value(self) -> float:
        return self._spin.value()

    def set_value(self, value: Any) -> None:
        self._spin.setValue(float(value))


class BoolWidget(QCheckBox, WidgetWrapper):
    def __init__(self, default: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setChecked(bool(default))

    def get_value(self) -> bool:
        return self.isChecked()

    def set_value(self, value: Any) -> None:
        self.setChecked(bool(value))


class EnumWidget(QComboBox, WidgetWrapper):
    def __init__(
        self,
        choices: list[Any],
        default: Any = None,
        optional: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        if optional:
            self.addItem("(none)", userData=None)
        for choice in choices:
            # store the real Python value as userData alongside the display string
            self.addItem(
                choice.value if isinstance(choice, Enum) else str(choice),
                userData=choice,
            )
        if default is not None:
            idx = self.findData(default)
            if idx >= 0:
                self.setCurrentIndex(idx)

    def get_value(self) -> Any:
        return self.currentData()

    def set_value(self, value: Any) -> None:
        idx = self.findData(value)
        if idx >= 0:
            self.setCurrentIndex(idx)


class TextAreaWidget(QPlainTextEdit, WidgetWrapper):
    def __init__(self, default: Any = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(80)
        if default is not None:
            self.setPlainText(json.dumps(default, indent=2, default=str))

    def get_value(self) -> Any:
        text = self.toPlainText().strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def set_value(self, value: Any) -> None:
        self.setPlainText(
            json.dumps(value, indent=2, default=str) if value is not None else ""
        )


class ObjectWidget(QWidget, WidgetWrapper):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.setColumnStretch(1, 1)
        self._fields: dict[str, WidgetWrapper] = {}
        self._row_count = 0

    def add_field(
        self, name: str, label: str, widget: WidgetWrapper, description: str = ""
    ) -> None:
        label_widget = FieldLabel(label, cast("QWidget", widget))
        label_widget.setWordWrap(True)
        label_widget.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        if description:
            label_widget.setToolTip(description)
        self._layout.addWidget(label_widget, self._row_count, 0)
        self._layout.addWidget(cast("QWidget", widget), self._row_count, 1)
        self._row_count += 1
        self._fields[name] = widget

    def get_value(self) -> dict:
        return {name: w.get_value() for name, w in self._fields.items()}

    def set_value(self, value: dict) -> None:
        if not isinstance(value, dict):
            return
        for name, w in self._fields.items():
            if name in value:
                w.set_value(value[name])


class OptionalWidget(QWidget, WidgetWrapper):
    def __init__(
        self,
        inner: WidgetWrapper,
        inline: bool = False,
        enabled_by_default: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._inner = cast("QWidget", inner)

        if inline:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self._checkbox = QCheckBox()
            layout.addWidget(self._checkbox)
            layout.addWidget(self._inner)
            layout.addStretch()
            self._checkbox.stateChanged.connect(
                lambda: self._inner.setVisible(self._checkbox.isChecked())
            )
            self._inner.setVisible(enabled_by_default)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self._checkbox = QCheckBox()
            layout.addWidget(self._checkbox)
            layout.addWidget(self._inner)
            layout.addStretch()
            self._checkbox.stateChanged.connect(
                lambda: self._inner.setVisible(self._checkbox.isChecked())
            )
            self._inner.setVisible(enabled_by_default)

        self._checkbox.setChecked(enabled_by_default)

    def get_value(self) -> Any:
        if not self._checkbox.isChecked():
            return None
        return cast("WidgetWrapper", self._inner).get_value()

    def set_value(self, value: Any) -> None:
        if value is None:
            self._checkbox.setChecked(False)
            self._inner.setVisible(False)
        else:
            self._checkbox.setChecked(True)
            self._inner.setVisible(True)
            inner = cast("WidgetWrapper", self._inner)
            inner.set_value(value)


class OptionalGroupWidget(QWidget, WidgetWrapper):
    def __init__(
        self, inner: ObjectWidget, enabled_by_default: bool = False, parent=None
    ):
        super().__init__(parent)
        self._inner = inner
        self._enabled = enabled_by_default

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self._checkbox_standalone = QCheckBox()
        self._group = QGroupBox()
        group_layout = QVBoxLayout(self._group)
        self._checkbox_in_group = QCheckBox()
        self._checkbox_in_group.setChecked(True)
        group_layout.addWidget(self._checkbox_in_group)
        group_layout.addWidget(inner)
        group_layout.addStretch()
        self._group.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
        )

        self._checkbox_standalone.stateChanged.connect(self._on_unchecked_toggled)
        self._checkbox_in_group.stateChanged.connect(self._on_checked_toggled)

        if enabled_by_default:
            self._layout.addWidget(self._group)
        else:
            self._layout.addWidget(self._checkbox_standalone)

    def _on_unchecked_toggled(self, state):
        if state:
            self._enabled = True
            self._checkbox_standalone.setParent(None)
            self._checkbox_in_group.setChecked(True)
            self._layout.addWidget(self._group)

    def _on_checked_toggled(self, state):
        if not state:
            self._enabled = False
            self._group.setParent(None)
            self._checkbox_standalone.setChecked(False)
            self._layout.addWidget(self._checkbox_standalone)

    def get_value(self) -> Any:
        return self._inner.get_value() if self._enabled else None

    def set_value(self, value: Any) -> None:
        if value is None:
            self._enabled = False
            self._group.setParent(None)
            self._checkbox_standalone.setChecked(False)
            self._layout.addWidget(self._checkbox_standalone)
        else:
            self._enabled = True
            self._checkbox_standalone.setParent(None)
            self._checkbox_in_group.setChecked(True)
            self._layout.addWidget(self._group)
            self._inner.set_value(value)


class GroupBoxWidget(QGroupBox, WidgetWrapper):
    """Plain (non-checkable) QGroupBox wrapping an ObjectWidget for required nested objects."""

    def __init__(
        self,
        inner: ObjectWidget,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._inner = inner
        layout = QVBoxLayout(self)
        layout.addWidget(inner)
        layout.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    def get_value(self) -> dict:
        return self._inner.get_value()

    def set_value(self, value: Any) -> None:
        self._inner.set_value(value)


class DiscriminatedUnionWidget(QWidget, WidgetWrapper):
    """
    Radio buttons + QStackedWidget for discriminated unions.

    One radio button per variant. Selecting a variant shows its extra fields
    (fields beyond the discriminator key) in a QStackedWidget below.
    Variants with no extra fields show nothing below the radio buttons.
    """

    def __init__(
        self,
        variants: list[tuple[str, type]],
        discriminator_key: str,
        build_object: Callable[[type, list[FieldInfo] | None], ObjectWidget],
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._discriminator_key = discriminator_key
        self._discriminator_values: list[str] = []
        self._empty_indices: set[int] = set()
        self._variant_widgets: list[QWidget] = []

        self._button_group = QButtonGroup(self)
        radio_row = QHBoxLayout()

        for i, (disc_value, variant_cls) in enumerate(variants):
            self._discriminator_values.append(disc_value)

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
        for i, widget in enumerate(self._variant_widgets):
            widget.setVisible(i == index and index not in self._empty_indices)

    def get_value(self) -> dict:
        index = self._button_group.checkedId()
        result = {self._discriminator_key: self._discriminator_values[index]}
        if index not in self._empty_indices:
            widget = self._variant_widgets[index]
            if isinstance(widget, WidgetWrapper):
                result.update(widget.get_value())
        return result

    def set_value(self, value: dict) -> None:
        disc_value = value.get(self._discriminator_key)
        if disc_value not in self._discriminator_values:
            return
        index = self._discriminator_values.index(disc_value)
        btn = self._button_group.button(index)
        if btn:
            btn.setChecked(True)
        self._on_selection_changed(index)
        if index not in self._empty_indices:
            widget = self._variant_widgets[index]
            if isinstance(widget, WidgetWrapper):
                widget.set_value(value)


def _get_field_infos_for_variant(cls: type):
    # import get_field_infos locally to avoid circular imports
    from fibsem_maestro.gui.form_builder.utils import get_field_infos

    return get_field_infos(cls)
