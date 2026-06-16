# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import contextlib
import dataclasses
from collections.abc import Callable
from typing import Any, cast, get_args

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from fibsem_maestro.gui.error import GUIError
from fibsem_maestro.gui.form_builder.utils import (
    FieldInfo,
    TypeKind,
    classify_type,
    get_field_infos,
)
from fibsem_maestro.gui.form_builder.widgets.action_select import ActionSelectWidget
from fibsem_maestro.gui.form_builder.widgets.area_selector.widget import (
    AreaSelectWidget,
)
from fibsem_maestro.gui.form_builder.widgets.bool import BoolWidget
from fibsem_maestro.gui.form_builder.widgets.detail_band import DetailBandWidget
from fibsem_maestro.gui.form_builder.widgets.enum import EnumWidget
from fibsem_maestro.gui.form_builder.widgets.float import FloatWidget
from fibsem_maestro.gui.form_builder.widgets.float_tuple import FloatTupleWidget
from fibsem_maestro.gui.form_builder.widgets.group_box import GroupBoxWidget
from fibsem_maestro.gui.form_builder.widgets.int import IntWidget
from fibsem_maestro.gui.form_builder.widgets.list import ListWidget
from fibsem_maestro.gui.form_builder.widgets.multi_select import MultiSelectWidget
from fibsem_maestro.gui.form_builder.widgets.object import ObjectWidget
from fibsem_maestro.gui.form_builder.widgets.optional import OptionalWidget
from fibsem_maestro.gui.form_builder.widgets.optional_group import OptionalGroupWidget
from fibsem_maestro.gui.form_builder.widgets.range_pair import RangePairWidget
from fibsem_maestro.gui.form_builder.widgets.string import StringWidget
from fibsem_maestro.gui.form_builder.widgets.text_area import TextAreaWidget
from fibsem_maestro.gui.form_builder.widgets.union import DiscriminatedUnionWidget
from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import WidgetType
from fibsem_maestro.workflow.workflow import Workflow

SCALAR_KINDS = {
    TypeKind.BOOL,
    TypeKind.INT,
    TypeKind.FLOAT,
    TypeKind.STR,
    TypeKind.ENUM,
    TypeKind.LITERAL,
}


class FormBuilder:
    """
    Builds a PyQt form from a live BaseSettings instance.

    The form is pre-populated with the current values of the settings instance.
    Every change in the form is immediately written back to the settings instance,
    triggering its reactive hooks.
    """

    def build_form(
        self,
        settings: BaseSettings,
        workflow: Workflow,
        fields: list[str] | None = None,
    ) -> ObjectWidget:
        """
        Build a form for a live settings instance.

        The form is pre-populated with current values and writes back
        reactively on every change.

        Args:
            settings: The live settings instance to bind to.
            workflow: The current workflow instance.
            fields: Optional list of field names to include. If None, all fields are shown.

        Returns:
            An ObjectWidget containing the complete form.
        """
        self._workflow = workflow
        self._microscope = self._workflow.microscope
        self._manufacturer_properties = self._microscope.control.manufacturer_prop_names

        field_infos = None
        if fields is not None:
            all_infos = get_field_infos(type(settings))
            field_infos = [fi for fi in all_infos if fi.name in fields]

        return self._build_object(type(settings), settings, field_infos)

    def _build_object(
        self,
        cls: type,
        settings: BaseSettings | None = None,
        field_infos: list[FieldInfo] | None = None,
    ) -> ObjectWidget:
        """
        Build an ObjectWidget for the given class, bound to a settings instance.

        Args:
            cls: The dataclass or Pydantic model class to introspect.
            settings: The live settings instance to pre-populate from and bind to.
                      None when building a sub-form with no live instance (e.g.
                      inside a DiscriminatedUnionWidget variant preview).
            field_infos: Pre-computed field infos, or None to compute from cls.

        Returns:
            A populated, reactive ObjectWidget.
        """
        obj = ObjectWidget()
        obj.setProperty("dataclass_form", True)
        infos = field_infos if field_infos is not None else get_field_infos(cls)

        for fi in infos:
            # get the live nested value for this field
            field_value = (
                getattr(settings, fi.name, None) if settings is not None else None
            )

            widget = self._build_field(fi, field_value, settings)

            # pre-populate scalar fields from the live value
            if field_value is not None and fi.kind in SCALAR_KINDS:
                with contextlib.suppress(Exception):
                    widget.set_value(field_value)

            obj.add_field(fi.name, fi.label, widget, fi.description)

        return obj

    def _build_field(
        self,
        fi: FieldInfo,
        field_value: Any,
        settings: BaseSettings | None,
    ) -> WidgetWrapper:
        """
        Dispatch a single FieldInfo to the appropriate widget and wire reactivity.

        Args:
            fi: Field metadata.
            field_value: Current value of this field from the live settings instance.
            settings: The parent settings instance to write back to on change.
        """
        if fi.hint is not None:
            inner = self._build_hinted_widget(fi, field_value, settings)
            if fi.optional:
                enabled = field_value is not None
                return OptionalWidget(inner, inline=True, enabled_by_default=enabled)
            return inner

        return self._build_typed_widget(fi, field_value, settings)

    def _build_hinted_widget(
        self,
        fi: FieldInfo,
        field_value: Any,
        settings: BaseSettings | None,
    ) -> WidgetWrapper:
        """Build the widget specified by fi.hint, pre-populated and reactive."""
        if (hint := fi.hint) is None:
            raise GUIError(f"Could not get hint for FieldInfo: {fi.name}.")

        suffix = fi.unit.suffix if fi.unit else None
        default = (
            field_value
            if field_value is not None
            else (fi.default if fi.default is not dataclasses.MISSING else None)
        )

        match hint.widget:
            case WidgetType.DROPDOWN:
                choices = hint.choices() if hint.choices else []
                widget = EnumWidget(
                    choices,
                    default=default,
                    optional=fi.optional,
                )

            case WidgetType.PROPERTY_SELECTOR:
                properties = hint.choices() if hint.choices else []
                manufacturer_properties = self._manufacturer_properties or []
                widget = EnumWidget(
                    properties + manufacturer_properties,
                    default=default,
                    optional=fi.optional,
                )

            case WidgetType.MULTI_SELECT:
                choices = hint.choices() if hint.choices else []
                widget = MultiSelectWidget(choices, default=default)

            case WidgetType.MULTI_PROPERTY_SELECTOR:
                properties = hint.choices() if hint.choices else []
                manufacturer_properties = self._manufacturer_properties or []
                widget = MultiSelectWidget(
                    properties + manufacturer_properties,
                    default=default,
                )

            case WidgetType.AREA_SELECT:
                widget = AreaSelectWidget(
                    microscope=self._microscope,
                    max_areas=hint.max_areas if hint.max_areas else None,
                    default=default,
                )

            case WidgetType.RANGE_PAIR:
                widget = RangePairWidget(
                    default=default,
                    minimum=fi.minimum,
                    maximum=fi.maximum,
                    suffix=suffix,
                )

            case WidgetType.DETAIL_BAND:
                return DetailBandWidget(
                    default=(default.low, default.high)
                    if default is not None
                    else None,
                    minimum=0.0,  # manual override
                    maximum=fi.maximum,
                    suffix=fi.unit.suffix if fi.unit else None,
                )

            case WidgetType.ACTION_SELECTOR:
                type_filter = fi.hint.action_type_filter if fi.hint is not None else []
                return ActionSelectWidget(
                    actions=self._workflow.actions,
                    type_filter=type_filter,
                    default=fi.default,
                    optional=fi.optional,
                )

            case _:
                widget = TextAreaWidget(default=default)

        if settings is not None:
            self._connect_widget(widget, fi, settings)

        return widget

    def _build_typed_widget(
        self,
        fi: FieldInfo,
        field_value: Any,
        settings: BaseSettings | None,
    ) -> WidgetWrapper:
        """
        Build a widget based purely on the field's TypeKind.

        Scalar fields are connected reactively to the settings instance.
        Nested dataclass fields recurse into _build_object with the nested
        settings instance, so each level binds independently.

        Args:
            fi: Field metadata.
            field_value: Current value from the live settings instance.
            settings: Parent settings instance to write back to.
        """
        suffix = fi.unit.suffix if fi.unit else None
        default = (
            field_value
            if field_value is not None
            else (fi.default if fi.default is not dataclasses.MISSING else None)
        )

        match fi.kind:
            case TypeKind.BOOL:
                widget = BoolWidget(
                    default=bool(default) if default is not None else False
                )
                if settings is not None:
                    self._connect_widget(widget, fi, settings)
                return self._maybe_optional(fi, widget, field_value)

            case TypeKind.INT:
                min_val = (
                    int(fi.minimum) + (1 if fi.minimum_exclusive else 0)
                    if fi.minimum is not None
                    else None
                )
                max_val = (
                    int(fi.maximum) - (1 if fi.maximum_exclusive else 0)
                    if fi.maximum is not None
                    else None
                )
                widget = IntWidget(
                    default=int(default) if default is not None else 0,
                    minimum=min_val,
                    maximum=max_val,
                    suffix=suffix,
                )
                if settings is not None:
                    self._connect_widget(widget, fi, settings)
                return self._maybe_optional(fi, widget, field_value)

            case TypeKind.FLOAT:
                widget = FloatWidget(
                    default=float(default) if default is not None else 0.0,
                    minimum=fi.minimum,
                    maximum=fi.maximum,
                    suffix=suffix,
                )
                if settings is not None:
                    self._connect_widget(widget, fi, settings)
                return self._maybe_optional(fi, widget, field_value)

            case TypeKind.STR:
                widget = StringWidget(
                    default=str(default) if default is not None else "",
                    suffix=suffix,
                )
                if settings is not None:
                    self._connect_widget(widget, fi, settings)
                return self._maybe_optional(fi, widget, field_value)

            case TypeKind.ENUM:
                widget = EnumWidget(
                    list(fi.inner_type),  # type: ignore
                    default=default,
                    optional=fi.optional,
                )
                if settings is not None:
                    self._connect_widget(widget, fi, settings)
                return widget

            case TypeKind.LITERAL:
                widget = EnumWidget(
                    fi.literal_choices or [],
                    default=default,
                    optional=fi.optional,
                )
                if settings is not None:
                    self._connect_widget(widget, fi, settings)
                return widget

            case TypeKind.DATACLASS:
                if fi.inner_type is None:
                    raise GUIError(
                        f"Expected inner type for dataclass field {fi.name}, got None"
                    )
                # recurse with the nested settings instance - no write-back needed
                # at this level since the nested object mutates itself reactively
                nested_settings = (
                    field_value if isinstance(field_value, fi.inner_type) else None
                )
                inner_obj = self._build_object(fi.inner_type, nested_settings)
                if fi.optional:
                    return OptionalGroupWidget(
                        inner_obj, enabled_by_default=nested_settings is not None
                    )
                return GroupBoxWidget(inner_obj)

            case TypeKind.DISCRIMINATED_UNION:
                from fibsem_maestro.gui.form_builder.utils import (
                    _get_discriminator_key,
                )

                if (union_variants := fi.union_variants) is None:
                    raise GUIError(
                        f"Expected union variants for field {fi.name}, got None"
                    )

                variant_types = [vt for _, vt in union_variants]

                if (discriminator_key := _get_discriminator_key(variant_types)) is None:
                    raise GUIError(
                        f"Could not determine discriminator key for field {fi.name}"
                    )

                union_widget = DiscriminatedUnionWidget(
                    variants=union_variants,
                    discriminator_key=discriminator_key,
                    build_object=lambda cls, infos: self._build_object(
                        cls,
                        field_value if isinstance(field_value, cls) else None,
                        infos,
                    ),
                )
                group = GroupBoxWidget(union_widget)
                if settings is not None:
                    self._connect_widget(group, fi, settings)
                if fi.optional:
                    return OptionalWidget(
                        group,
                        inline=False,
                        enabled_by_default=field_value is not None,
                    )
                return group

            case TypeKind.LIST:
                args = get_args(fi.inner_type)
                if args:
                    inner_type = args[0]
                    widget = ListWidget(
                        item_factory=self._make_item_factory(inner_type),
                        default=list(default) if default is not None else [],
                    )
                else:
                    widget = TextAreaWidget(default=default)
                if settings is not None:
                    self._connect_widget(widget, fi, settings)
                return self._maybe_optional(fi, widget, field_value)

            case TypeKind.FLOAT_TUPLE:
                args = get_args(fi.inner_type)
                length = len(args)
                widget = FloatTupleWidget(
                    length=length,
                    default=tuple(default) if default is not None else None,
                )
                if settings is not None:
                    self._connect_widget(widget, fi, settings)
                return self._maybe_optional(fi, widget, field_value)

            case TypeKind.UNKNOWN:
                widget = TextAreaWidget(default=default)
                if settings is not None:
                    self._connect_widget(widget, fi, settings)
                return self._maybe_optional(fi, widget, field_value)

    def _connect_widget(
        self,
        widget: WidgetWrapper,
        fi: FieldInfo,
        settings: BaseSettings,
    ) -> None:
        """
        Connect a widget's change signal to write its value back to settings.

        Tries to connect the widget itself first. If the widget is a compound
        wrapper, searches its children for known Qt input types instead.

        Args:
            widget: The WidgetWrapper to connect.
            fi: Field metadata identifying the settings attribute to write to.
            settings: The live settings instance to write back to.
        """

        def write_back(_=None) -> None:
            with contextlib.suppress(Exception):
                setattr(settings, fi.name, widget.get_value())

        def connect_qt_widget(w: QWidget) -> bool:
            """Connect the appropriate signal of a Qt leaf widget.

            Returns:
                True if a signal was connected, False if the widget type
                is not a known input type.
            """
            match w:
                case QSpinBox():
                    w.valueChanged.connect(write_back)
                case QDoubleSpinBox():
                    w.valueChanged.connect(write_back)
                case QLineEdit():
                    w.textChanged.connect(write_back)
                case QCheckBox():
                    w.stateChanged.connect(write_back)
                case QComboBox():
                    w.currentIndexChanged.connect(write_back)
                case QPlainTextEdit():
                    w.textChanged.connect(write_back)
                case QAbstractItemView():
                    w.selectionModel().selectionChanged.connect(write_back)
                case _:
                    return False
            return True

        # try the widget itself first, then fall back to searching children
        if not connect_qt_widget(cast("QWidget", widget)):
            for child_type in (
                QSpinBox,
                QDoubleSpinBox,
                QLineEdit,
                QCheckBox,
                QComboBox,
                QPlainTextEdit,
                QAbstractItemView,
            ):
                for child in cast("QWidget", widget).findChildren(child_type):
                    connect_qt_widget(cast("QWidget", child))

    def _maybe_optional(
        self,
        fi: FieldInfo,
        inner: WidgetWrapper,
        field_value: Any,
    ) -> WidgetWrapper:
        """
        Wrap inner in an OptionalWidget if the field is optional.

        Args:
            fi: Field metadata.
            inner: The widget to optionally wrap.
            field_value: Current live value, used to determine enabled state.
        """
        if not fi.optional:
            return inner
        inline = fi.kind in SCALAR_KINDS
        return OptionalWidget(
            inner,
            inline=inline,
            enabled_by_default=field_value is not None,
        )

    def _make_item_factory(self, inner_type: type) -> Callable[[], WidgetWrapper]:
        """Return a factory that creates a widget for a single list item."""
        kind = classify_type(inner_type)

        match kind:
            case TypeKind.BOOL:
                return lambda: BoolWidget()
            case TypeKind.INT:
                return lambda: IntWidget()
            case TypeKind.FLOAT:
                return lambda: FloatWidget()
            case TypeKind.STR:
                return lambda: StringWidget()
            case TypeKind.ENUM:
                return lambda: EnumWidget(list(inner_type))  # type: ignore
            case TypeKind.DATACLASS:
                return lambda: GroupBoxWidget(self._build_object(inner_type, None))
            case _:
                return lambda: TextAreaWidget()
