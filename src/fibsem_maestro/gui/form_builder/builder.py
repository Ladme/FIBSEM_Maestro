# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from typing import Any

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.form_builder._write_back import WriteBack
from fibsem_maestro.gui.form_builder.schema.constraints import NumericBounds
from fibsem_maestro.gui.form_builder.schema.field_info import FieldInfo
from fibsem_maestro.gui.form_builder.schema.field_type import (
    BoolType,
    DataclassType,
    DiscriminatedUnionType,
    EnumType,
    FieldType,
    FloatTupleType,
    FloatType,
    IntType,
    ListType,
    LiteralType,
    StrType,
    UnknownType,
    is_scalar,
)
from fibsem_maestro.gui.form_builder.schema.schema import get_field_infos
from fibsem_maestro.gui.form_builder.widgets.action_select import ActionSelectWidget
from fibsem_maestro.gui.form_builder.widgets.area_select.widget import (
    AreaSelectWidget,
)
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget, OnChange, _noop
from fibsem_maestro.gui.form_builder.widgets.bool import BoolWidget
from fibsem_maestro.gui.form_builder.widgets.detail_band import DetailBandWidget
from fibsem_maestro.gui.form_builder.widgets.enum import EnumWidget
from fibsem_maestro.gui.form_builder.widgets.float import FloatWidget
from fibsem_maestro.gui.form_builder.widgets.float_tuple import FloatTupleWidget
from fibsem_maestro.gui.form_builder.widgets.group_wrapper import GroupWrapper
from fibsem_maestro.gui.form_builder.widgets.int import IntWidget
from fibsem_maestro.gui.form_builder.widgets.list import ListWidget
from fibsem_maestro.gui.form_builder.widgets.multi_select import MultiSelectWidget
from fibsem_maestro.gui.form_builder.widgets.object import ObjectWidget
from fibsem_maestro.gui.form_builder.widgets.optional import OptionalWidget
from fibsem_maestro.gui.form_builder.widgets.range_pair import RangePairWidget
from fibsem_maestro.gui.form_builder.widgets.string import StringWidget
from fibsem_maestro.gui.form_builder.widgets.text_area import TextAreaWidget
from fibsem_maestro.gui.form_builder.widgets.union import DiscriminatedUnionWidget
from fibsem_maestro.gui.workflow_manager import WorkflowManager
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import WidgetType


class FormBuilder:
    """Builds a reactive PyQt form from a live reactive settings instance."""

    def build_form(
        self,
        settings: BaseSettings,
        workflow_manager: WorkflowManager,
        fields: list[str] | None = None,
        action: Action | None = None,
    ) -> ObjectWidget:
        """
        Build a form bound to a live settings instance.

        The form is pre-populated with current values and writes each top-level
        field back to `settings` reactively on every change.

        Args:
            settings: The live reactive settings instance.
            workflow_manager: Provides the microscope, action list, and signals.
            fields: Optional subset of top-level field names to include.
            action: If set, the action whose `action_changed` signal is
                emitted after each successful write-back.

        Returns:
            The populated, reactive top-level `ObjectWidget`.
        """
        self._configure(workflow_manager, action)
        return self._build_object(
            type(settings), settings, self._infos(type(settings), fields)
        )

    def build_fields(
        self,
        cls: type,
        fields: list[str] | None = None,
        workflow_manager: WorkflowManager | None = None,
    ) -> ObjectWidget:
        """
        Build a non-reactive form for a class, or a subset of its fields.

        Unlike `build_form`, this binds to no live instance; the caller reads
        values back via the returned widget's `get_value()`. Use it for one-shot
        forms where no settings object exists yet.

        Args:
            cls: The dataclass or model class to build a form for.
            fields: Optional subset of field names to include.
            workflow_manager: Only required if an included field uses a
                manager-dependent widget (property/area/action selectors); may be
                None otherwise.

        Returns:
            A populated, value-only `ObjectWidget`.
        """

        self._configure(workflow_manager, action=None)
        return self._build_object(
            cls, settings=None, field_infos=self._infos(cls, fields)
        )

    def _configure(
        self, workflow_manager: WorkflowManager | None, action: Action | None
    ) -> None:
        """
        Resolve manager-derived state for the current build.
        """
        self._manager = workflow_manager
        self._microscope = (
            workflow_manager.workflow.microscope if workflow_manager else None
        )
        self._manufacturer_properties = (
            self._microscope.control.manufacturer_prop_names if self._microscope else []
        )
        self._action = action

    def _infos(self, cls: type, fields: list[str] | None) -> list[FieldInfo]:
        """Return field infos for `cls`, optionally filtered to `fields`."""
        infos = get_field_infos(cls)
        if fields is not None:
            infos = [fi for fi in infos if fi.name in fields]
        return infos

    def _build_object(
        self,
        cls: type,
        settings: BaseSettings | None,
        field_infos: list[FieldInfo] | None = None,
        on_change: OnChange = _noop,
    ) -> ObjectWidget:
        """Build an `ObjectWidget` for `cls`.

        There are two modes, distinguished by `settings`:

        - Live root (`settings` is not None): this is the top level, so
            each field gets its own write-back, threaded through that field's
            subtree as `on_change`.
        - Value-only (`settings` is None): a nested composite or union
            preview. No write-backs are created; the inherited `on_change` is
            threaded down, so edits still reach the one top-level write-back.

        Args:
            cls: The dataclass or model class to introspect.
            settings: The live root instance, or None for a value-only subtree.
            field_infos: Pre-computed field infos, or None to compute from cls.
            on_change: The callback threaded down in value-only mode.

        Returns:
            A populated `ObjectWidget`.
        """
        obj = ObjectWidget(cls=cls)
        infos = field_infos if field_infos is not None else get_field_infos(cls)

        for fi in infos:
            value = getattr(settings, fi.name, None) if settings is not None else None

            if settings is not None:
                # top-level field: its own write-back drives the whole subtree
                write_back = WriteBack(settings, fi, self._manager, self._action)
                widget = self._build_field(fi, value, write_back)
                write_back.bind(widget)
            else:
                # nested: reuse the inherited top-level write-back
                widget = self._build_field(fi, value, on_change)

            obj.add_field(fi.name, fi.label, widget, fi.description)

        return obj

    def _build_field(
        self, fi: FieldInfo, value: Any, on_change: OnChange
    ) -> BaseWidget:
        """
        Dispatch a single field to a widget and wire `on_change`.

        A field with a `FormHint` takes the hinted path; otherwise it is
        dispatched purely based on its `FieldType` descriptor.
        """
        if fi.hint is not None:
            inner = self._build_hinted_widget(fi, value)
            result: BaseWidget = inner
            if fi.optional:
                result = OptionalWidget(
                    inner, inline=True, enabled_by_default=value is not None
                )

            # connect the value editor and, if wrapped, the optional toggle
            inner.on_change(on_change)
            if result is not inner:
                result.on_change(on_change)
            return result

        return self._build_typed_widget(fi, value, on_change)

    def _build_hinted_widget(self, fi: FieldInfo, value: Any) -> BaseWidget:
        """
        Build the widget specified by `fi.hint` (unconnected).

        `on_change` is connected by `_build_field` after any optional-wrapping,
        so the outermost changing widget is wired.
        """
        hint = fi.hint
        if hint is None:
            raise ValueError(f"no hint for field {fi.name!r}")

        suffix = fi.unit.suffix if fi.unit else None
        default = self._resolve_default(fi, value)
        min_val, max_val = self._float_bounds(fi.bounds)

        match hint.widget:
            case WidgetType.DROPDOWN:
                choices = hint.choices() if hint.choices else []
                return EnumWidget(choices, default=default, optional=fi.optional)

            case WidgetType.PROPERTY_SELECTOR:
                properties = hint.choices() if hint.choices else []
                properties = properties + (self._manufacturer_properties or [])
                return EnumWidget(properties, default=default, optional=fi.optional)

            case WidgetType.MULTI_SELECT:
                choices = hint.choices() if hint.choices else []
                return MultiSelectWidget(choices, default=default)

            case WidgetType.MULTI_PROPERTY_SELECTOR:
                properties = hint.choices() if hint.choices else []
                properties = properties + (self._manufacturer_properties or [])
                return MultiSelectWidget(properties, default=default)

            case WidgetType.AREA_SELECT:
                return AreaSelectWidget(
                    microscope=self._microscope,
                    max_areas=hint.max_areas if hint.max_areas else None,
                    default=default,
                )

            case WidgetType.RANGE_PAIR:
                return RangePairWidget(
                    default=default, minimum=min_val, maximum=max_val, suffix=suffix
                )

            case WidgetType.DETAIL_BAND:
                return DetailBandWidget(
                    default=default,
                    minimum=0.0,  # manual override
                    maximum=max_val,
                    suffix=suffix,
                )

            case WidgetType.ACTION_SELECTOR:
                if self._manager is None:
                    raise ValueError(
                        f"field {fi.name!r} needs a workflow_manager, but none was given"
                    )

                widget = ActionSelectWidget(
                    actions=self._manager.workflow.actions,
                    type_filter=hint.action_type_filter,
                    default=default,
                    optional=fi.optional,
                )
                # rebuild the dropdown when actions are added/removed or renamed
                self._manager.actions_changed.connect(widget.on_actions_changed)
                self._manager.action_changed.connect(widget.on_action_changed)
                return widget

            case _:
                return TextAreaWidget(self._fallback_type(fi.type), default=default)

    def _build_typed_widget(
        self, fi: FieldInfo, value: Any, on_change: OnChange
    ) -> BaseWidget:
        """
        Build a widget from the field's `FieldType` descriptor.

        Scalars and dynamic wrappers (optional, list, union) get `on_change`
        connected. Nested composites thread `on_change` to their children and
        need no connection of their own.
        """
        default = self._resolve_default(fi, value)
        suffix = fi.unit.suffix if fi.unit else None

        match fi.type:
            case BoolType():
                widget = BoolWidget(
                    default=bool(default) if default is not None else False
                )
                return self._finish_leaf(fi, widget, value, on_change)

            case IntType():
                min_val, max_val = self._int_bounds(fi.bounds)
                widget = IntWidget(
                    default=int(default) if default is not None else 0,
                    minimum=min_val,
                    maximum=max_val,
                    suffix=suffix,
                )
                return self._finish_leaf(fi, widget, value, on_change)

            case FloatType():
                min_val, max_val = self._float_bounds(fi.bounds)
                widget = FloatWidget(
                    default=float(default) if default is not None else 0.0,
                    minimum=min_val,
                    maximum=max_val,
                    suffix=suffix,
                )
                return self._finish_leaf(fi, widget, value, on_change)

            case StrType():
                widget = StringWidget(
                    default=str(default) if default is not None else "", suffix=suffix
                )
                return self._finish_leaf(fi, widget, value, on_change)

            case EnumType(enum_type=enum_cls):
                # optionality handled inside EnumWidget (adds a "(none)" entry)
                widget = EnumWidget(
                    list(enum_cls), default=default, optional=fi.optional
                )
                widget.on_change(on_change)
                return widget

            case LiteralType(choices=choices):
                widget = EnumWidget(
                    list(choices), default=default, optional=fi.optional
                )
                widget.on_change(on_change)
                return widget

            case DataclassType(model=model):
                # value-only recursion: thread the same write-back to children
                inner_obj = self._build_object(
                    model, settings=None, on_change=on_change
                )
                if fi.optional:
                    # toggling None <-> instance is a change to the parent field
                    group = OptionalWidget(
                        GroupWrapper(inner_obj),
                        inline=False,
                        enabled_by_default=value is not None,
                    )
                    group.on_change(on_change)
                    return group
                return GroupWrapper(inner_obj)

            case DiscriminatedUnionType(discriminator_key=key, variants=variants):
                union_widget = DiscriminatedUnionWidget(
                    variants=[
                        (v.discriminator_value, v.variant_type) for v in variants
                    ],
                    discriminator_key=key,
                    build_object=lambda cls, infos: self._build_object(
                        cls, settings=None, field_infos=infos, on_change=on_change
                    ),
                )

                # switching variants is a change
                union_widget.on_change(on_change)
                if value is not None:
                    union_widget.set_value(value)

                group = GroupWrapper(union_widget)
                if fi.optional:
                    result = OptionalWidget(
                        group, inline=False, enabled_by_default=value is not None
                    )
                    result.on_change(on_change)
                    return result

                return group

            case ListType(item=item):
                widget = ListWidget(
                    item_factory=self._make_item_factory(item, on_change),
                    default=list(default) if default is not None else [],
                )
                return self._finish_leaf(fi, widget, value, on_change)

            case FloatTupleType(length=length):
                widget = FloatTupleWidget(
                    length=length,
                    default=tuple(default) if default is not None else None,
                )
                return self._finish_leaf(fi, widget, value, on_change)

            case UnknownType(hint=target_type):
                widget = TextAreaWidget(target_type, default=default)
                return self._finish_leaf(fi, widget, value, on_change)

            case field_type:
                raise ValueError(f"Unknown field type: {field_type}")

    def _make_item_factory(
        self, item: FieldType, on_change: OnChange
    ) -> Callable[[], BaseWidget]:
        """
        Return a factory building a widget for a single list element.

        The element's `on_change` is the same top-level write-back, so editing
        any item reconstructs and reassigns the whole list field.
        """
        match item:
            case BoolType():
                return lambda: self._wire_leaf(BoolWidget(), on_change)
            case IntType():
                return lambda: self._wire_leaf(IntWidget(), on_change)
            case FloatType():
                return lambda: self._wire_leaf(FloatWidget(), on_change)
            case StrType():
                return lambda: self._wire_leaf(StringWidget(), on_change)
            case EnumType(enum_type=enum_cls):
                return lambda: self._wire_leaf(EnumWidget(list(enum_cls)), on_change)
            case DataclassType(model=model):
                return lambda: GroupWrapper(
                    self._build_object(model, settings=None, on_change=on_change)
                )
            case _:
                return lambda: self._wire_leaf(
                    TextAreaWidget(self._fallback_type(item)), on_change
                )

    def _finish_leaf(
        self, fi: FieldInfo, widget: BaseWidget, value: Any, on_change: OnChange
    ) -> BaseWidget:
        """
        Optionally wrap a leaf, then connect `on_change` to the value editor and (if wrapped) the optional toggle.
        """
        result = self._maybe_optional(fi, widget, value)
        widget.on_change(on_change)

        if result is not widget:
            result.on_change(on_change)

        return result

    def _wire_leaf(self, widget: BaseWidget, on_change: OnChange) -> BaseWidget:
        """Connect `on_change` to a leaf and return it (used by item factories)."""
        widget.on_change(on_change)
        return widget

    def _maybe_optional(
        self, fi: FieldInfo, inner: BaseWidget, value: Any
    ) -> BaseWidget:
        """Wrap `inner` in an `OptionalWidget` when the field is optional."""
        if not fi.optional:
            return inner
        return OptionalWidget(
            inner, inline=is_scalar(fi.type), enabled_by_default=value is not None
        )

    def _resolve_default(self, fi: FieldInfo, value: Any) -> Any:
        """Prefer the live value, else the field's declared default, else None."""
        if value is not None:
            return value
        if fi.default is not None:
            return fi.default.value
        return None

    def _int_bounds(
        self, bounds: NumericBounds | None
    ) -> tuple[int | None, int | None]:
        """Convert numeric bounds to inclusive integer min/max for a spin box."""
        if bounds is None:
            return None, None

        minimum = (
            None
            if bounds.minimum is None
            else int(bounds.minimum.value) + (1 if bounds.minimum.exclusive else 0)
        )

        maximum = (
            None
            if bounds.maximum is None
            else int(bounds.maximum.value) - (1 if bounds.maximum.exclusive else 0)
        )

        return minimum, maximum

    def _float_bounds(
        self, bounds: NumericBounds | None
    ) -> tuple[float | None, float | None]:
        """Return raw float min/max (exclusivity is not represented for floats)."""
        if bounds is None:
            return None, None
        minimum = None if bounds.minimum is None else bounds.minimum.value
        maximum = None if bounds.maximum is None else bounds.maximum.value
        return minimum, maximum

    def _fallback_type(self, field_type: FieldType) -> Any:
        """The type a YAML text-area fallback should load values into."""
        if isinstance(field_type, UnknownType):
            return field_type.hint
        if isinstance(field_type, DataclassType):
            return field_type.model
        return Any
