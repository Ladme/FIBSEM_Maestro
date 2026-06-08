# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import dataclasses

from PyQt6.QtWidgets import QScrollArea

from fibsem_maestro.gui.error import GUIError
from fibsem_maestro.gui.form_builder.utils import (
    FieldInfo,
    TypeKind,
    class_name_to_label,
    get_field_infos,
)
from fibsem_maestro.gui.form_builder.widgets.area_selector.widget import (
    AreaSelectWidget,
)
from fibsem_maestro.gui.form_builder.widgets.bool import BoolWidget
from fibsem_maestro.gui.form_builder.widgets.enum import EnumWidget
from fibsem_maestro.gui.form_builder.widgets.float import FloatWidget
from fibsem_maestro.gui.form_builder.widgets.group_box import GroupBoxWidget
from fibsem_maestro.gui.form_builder.widgets.int import IntWidget
from fibsem_maestro.gui.form_builder.widgets.multi_select import MultiSelectWidget
from fibsem_maestro.gui.form_builder.widgets.object import ObjectWidget
from fibsem_maestro.gui.form_builder.widgets.optional import OptionalWidget
from fibsem_maestro.gui.form_builder.widgets.optional_group import OptionalGroupWidget
from fibsem_maestro.gui.form_builder.widgets.range_pair import RangePairWidget
from fibsem_maestro.gui.form_builder.widgets.string import StringWidget
from fibsem_maestro.gui.form_builder.widgets.text_area import TextAreaWidget
from fibsem_maestro.gui.form_builder.widgets.union import DiscriminatedUnionWidget
from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import WidgetType

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
    Builds a scrollable PyQt form from a dataclass or Pydantic BaseModel class.
    """

    def build_form(
        self, cls: type[BaseSettings], microscope: Microscope | None = None
    ) -> ObjectWidget:
        """
        Entry point. Returns a widget containing the complete form.
        """
        self._microscope = microscope
        self._manufacturer_properties = (
            microscope.control.manufacturer_prop_names if microscope is not None else []
        )
        return self._build_object(cls)

    def collect_values(self, form: ObjectWidget) -> dict:
        """
        Walk the widget tree and return a plain dict of all field values.
        """
        return form.get_value()

    def _build_object(
        self, cls: type, field_infos: list[FieldInfo] | None = None
    ) -> ObjectWidget:
        """
        Build an ObjectWidget from a dataclass class.
        """
        obj = ObjectWidget()
        infos = field_infos if field_infos is not None else get_field_infos(cls)

        for fi in infos:
            widget = self._build_field(fi)
            obj.add_field(fi.name, fi.label, widget, fi.description)

        return obj

    def _build_field(self, fi: FieldInfo) -> WidgetWrapper:
        """
        Dispatch a single FieldInfo to the appropriate widget.
        """
        # FormHint takes priority - build the hinted widget, then wrap if optional
        if fi.hint is not None:
            inner = self._build_hinted_widget(fi)
            if fi.optional:
                enabled = (
                    fi.default is not None and fi.default is not dataclasses.MISSING
                )
                return OptionalWidget(inner, inline=True, enabled_by_default=enabled)
            return inner

        # default dispatch
        return self._build_typed_widget(fi)

    def _build_hinted_widget(self, fi: FieldInfo) -> WidgetWrapper:
        """Build the widget specified by fi.hint.widget."""
        if (hint := fi.hint) is None:
            raise GUIError(f"Could not get hint for FieldInfo: {fi.name}.")

        suffix = fi.unit.suffix if fi.unit else None
        default = fi.default if fi.default is not dataclasses.MISSING else None

        match hint.widget:
            case WidgetType.DROPDOWN:
                choices = hint.choices() if hint.choices else []
                return EnumWidget(
                    choices,
                    default=default,
                    optional=fi.optional,
                )
            case WidgetType.PROPERTY_SELECTOR:
                properties = hint.choices() if hint.choices else []
                manufacturer_properties = self._manufacturer_properties or []
                return EnumWidget(
                    properties + manufacturer_properties,
                    default=default,
                    optional=fi.optional,
                )

            case WidgetType.MULTI_SELECT:
                choices = hint.choices() if hint.choices else []
                return MultiSelectWidget(choices, default=default)

            case WidgetType.MULTI_PROPERTY_SELECTOR:
                properties = hint.choices() if hint.choices else []
                manufacturer_properties = self._manufacturer_properties or []
                return MultiSelectWidget(
                    properties + manufacturer_properties,
                    default=default,
                )

            case WidgetType.AREA_SELECT:
                return AreaSelectWidget(
                    microscope=self._microscope,
                    max_areas=hint.max_areas if hint.max_areas else None,
                    default=default,
                )
            case WidgetType.RANGE_PAIR:
                return RangePairWidget(
                    default=default,
                    minimum=fi.minimum,
                    maximum=fi.maximum,
                    suffix=suffix,
                )

            case _:
                return TextAreaWidget()

    def _build_typed_widget(self, fi: FieldInfo) -> WidgetWrapper:
        """
        Build a widget based purely on the field's TypeKind.
        Wraps in OptionalWidget when fi.optional is True.
        """

        suffix = fi.unit.suffix if fi.unit else None
        default = fi.default if fi.default is not dataclasses.MISSING else None

        match fi.kind:
            case TypeKind.BOOL:
                widget = BoolWidget(
                    default=bool(default) if default is not None else False
                )

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

            case TypeKind.FLOAT:
                widget = FloatWidget(
                    default=float(default) if default is not None else 0.0,
                    minimum=fi.minimum,
                    maximum=fi.maximum,
                    suffix=suffix,
                )

            case TypeKind.STR:
                widget = StringWidget(
                    default=str(default) if default is not None else "",
                    suffix=suffix,
                )

            case TypeKind.ENUM:
                # EnumWidget handles its own optional sentinel
                return EnumWidget(
                    list(fi.inner_type),  # type: ignore
                    default=default,
                    optional=fi.optional,
                )

            case TypeKind.LITERAL:
                # EnumWidget handles its own optional sentinel
                return EnumWidget(
                    fi.literal_choices or [], default=default, optional=fi.optional
                )

            case TypeKind.DATACLASS:
                if fi.inner_type is None:
                    raise GUIError(
                        f"Expected inner type for dataclass field {fi.name}, got None"
                    )
                inner_obj = self._build_object(fi.inner_type)
                if fi.optional:
                    return OptionalGroupWidget(
                        inner_obj, enabled_by_default=default is not None
                    )
                return GroupBoxWidget(inner_obj)

            case TypeKind.DISCRIMINATED_UNION:
                from fibsem_maestro.gui.form_builder.utils import _get_discriminator_key

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
                    build_object=self._build_object,
                )
                group = GroupBoxWidget(union_widget)
                if fi.optional:
                    return OptionalWidget(
                        group, inline=False, enabled_by_default=default is not None
                    )
                return group

            case TypeKind.LIST | TypeKind.UNKNOWN:
                widget = TextAreaWidget(default=default)

        return self._maybe_optional(fi, widget)

    def _maybe_optional(self, fi: FieldInfo, inner: WidgetWrapper) -> WidgetWrapper:
        """
        Wrap inner in an OptionalWidget if the field is optional.
        For scalar widgets (int, float, str, bool) an optional field with a
        non-None default is shown enabled by default.
        """
        if not fi.optional:
            return inner
        default = fi.default if fi.default is not dataclasses.MISSING else None
        inline = fi.kind in SCALAR_KINDS
        return OptionalWidget(
            inner, inline=inline, enabled_by_default=default is not None
        )
