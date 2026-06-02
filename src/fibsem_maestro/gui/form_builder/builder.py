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
from fibsem_maestro.gui.form_builder.widgets import (
    BoolWidget,
    DiscriminatedUnionWidget,
    EnumWidget,
    FloatWidget,
    GroupBoxWidget,
    IntWidget,
    ObjectWidget,
    OptionalGroupWidget,
    OptionalWidget,
    StringWidget,
    TextAreaWidget,
    WidgetWrapper,
)
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

    def build_form(self, cls: type) -> QScrollArea:
        """
        Entry point.

        Returns a QScrollArea containing the complete form.
        Embed this widget anywhere in your application layout.
        """
        inner = self._build_object(cls)

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        return scroll

    def collect_values(self, form: QScrollArea) -> dict:
        """
        Walk the widget tree and return a plain dict of all field values.
        """
        inner = form.widget()
        return inner.get_value() if isinstance(inner, WidgetWrapper) else {}

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
                return EnumWidget(choices, default=default, optional=fi.optional)

            case WidgetType.CHIPS:
                # TODO: ChipSelectorWidget
                return TextAreaWidget(default=default)

            case WidgetType.YAML_EDITOR:
                # TODO: YamlEditorWidget
                return TextAreaWidget(default=default)

            case WidgetType.FILE_PATH | WidgetType.DIRECTORY_PATH:
                # TODO: replace with file/dir selector
                return StringWidget(
                    default=str(default) if default is not None else "", suffix=suffix
                )

            case WidgetType.RANGE_PAIR:
                # TODO: replace with RangePairWidget
                return TextAreaWidget(default=default)

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
                widget = IntWidget(
                    default=int(default) if default is not None else 0,
                    minimum=fi.minimum,
                    maximum=fi.maximum,
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
