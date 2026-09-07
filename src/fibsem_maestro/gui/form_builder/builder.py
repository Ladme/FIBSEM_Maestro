# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING, Any

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.form_builder._build_scope import (
    BuildContext,
    BuildScope,
    resolve_beam,
)
from fibsem_maestro.gui.form_builder._overlay_binding import OverlayBinding
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
from fibsem_maestro.gui.form_builder.widgets.area_select.overlay import OverlayData
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
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import AreaOverlay, WidgetType

if TYPE_CHECKING:
    from fibsem_maestro.core.pattern_type import PatternType
    from fibsem_maestro.microscope.microscope import Microscope


class FormBuilder:
    """Builds a reactive PyQt form from a live reactive settings instance."""

    def __init__(self) -> None:
        """Initialise the per-build configuration to empty."""
        self._txt_log: TextLogger | None = None
        self._manager: WorkflowManager | None = None
        self._microscope: Microscope | None = None
        self._manufacturer_properties: list[str] = []
        self._action: Action | None = None

    def build_form(
        self,
        settings: BaseSettings,
        workflow_manager: WorkflowManager,
        txt_log: TextLogger,
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
            txt_log: The text logger to use for logging.
            fields: Optional subset of top-level field names to include.
            action: If set, the action whose `action_changed` signal is
                emitted after each successful write-back.

        Returns:
            The populated, reactive top-level `ObjectWidget`.
        """
        self._txt_log = txt_log
        self._configure(workflow_manager, action)
        return self._build_root(
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
        return self._build_root(cls, settings=None, infos=self._infos(cls, fields))

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

    def _warn(self, message: str) -> None:
        """Log a build-time warning, if a logger was supplied."""
        if self._txt_log is not None:
            self._txt_log.warning(message)

    def _build_root(
        self, cls: type, settings: BaseSettings | None, infos: list[FieldInfo]
    ) -> ObjectWidget:
        """
        Build the top-level object, then wire overlays across the finished tree.

        Args:
            cls: The dataclass or model class at the form root.
            settings: The live root instance, or None for a value-only form.
            infos: Field infos for the root object.

        Returns:
            The populated top-level `ObjectWidget`.
        """
        context = BuildContext()
        scope = BuildScope(context=context)
        try:
            obj = self._build_object(cls, settings, scope, field_infos=infos)
        finally:
            context.building = False
        self._flush_overlays(context)
        return obj

    def _build_object(
        self,
        cls: type,
        settings: BaseSettings | None,
        scope: BuildScope,
        field_infos: list[FieldInfo] | None = None,
        on_change: OnChange = _noop,
    ) -> ObjectWidget:
        """
        Build an `ObjectWidget` for `cls`.

        There are two modes, distinguished by `settings`:

        - Live root (`settings` is not None): this is the top level, so
            each field gets its own write-back, threaded through that field's
            subtree as `on_change`.
        - Value-only (`settings` is None): a nested composite or union
            preview. No write-backs are created; the inherited `on_change` is
            threaded down, so edits still reach the one top-level write-back.

        Each addressable field's widget is registered in the build context, so
        overlays declared elsewhere in the form can reference it by path.

        Args:
            cls: The dataclass or model class to introspect.
            settings: The live root instance, or None for a value-only subtree.
            scope: The scope this object occupies.
            field_infos: Pre-computed field infos, or None to compute from cls.
            on_change: The callback threaded down in value-only mode.

        Returns:
            A populated `ObjectWidget`.
        """
        # live instances enclosing this object are extended by this one
        scope = scope.with_instance(settings)

        obj = ObjectWidget(cls=cls)
        infos = field_infos if field_infos is not None else get_field_infos(cls)

        widgets: dict[str, BaseWidget] = {}
        for fi in infos:
            value = getattr(settings, fi.name, None) if settings is not None else None
            field_scope = scope.child(fi.name)

            if settings is not None:
                # top-level field: its own write-back drives the whole subtree
                write_back = WriteBack(
                    settings,
                    fi,
                    self._manager,
                    self._action,
                    self._txt_log,  # ty:ignore[invalid-argument-type]
                )
                widget = self._build_field(fi, value, write_back, field_scope)
                write_back.bind(widget)
            else:
                # nested: reuse the inherited top-level write-back
                widget = self._build_field(fi, value, on_change, field_scope)

            obj.add_field(fi.name, fi.label, widget, fi.description)
            widgets[fi.name] = widget
            if (path := field_scope.dotted) is not None:
                scope.context.widgets[path] = widget

        self._collect_overlays(infos, widgets, scope)
        return obj

    def _build_field(
        self, fi: FieldInfo, value: Any, on_change: OnChange, scope: BuildScope
    ) -> BaseWidget:
        """
        Dispatch a single field to a widget and wire `on_change`.

        A field with a `FormHint` takes the hinted path; otherwise it is
        dispatched purely based on its `FieldType` descriptor.
        """
        if fi.hint is not None:
            inner = self._build_hinted_widget(fi, value, scope)
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

        return self._build_typed_widget(fi, value, on_change, scope)

    def _build_hinted_widget(
        self, fi: FieldInfo, value: Any, scope: BuildScope
    ) -> BaseWidget:
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

            case WidgetType.PATTERN_TYPE_SELECTOR:
                choices: list[PatternType] = (
                    self._microscope.control.available_patterns
                    if self._microscope is not None
                    else []
                )
                return EnumWidget(
                    choices,
                    default=default,
                    optional=fi.optional,
                )

            case WidgetType.MULTI_SELECT:
                choices = hint.choices() if hint.choices else []
                return MultiSelectWidget(choices, default=default)

            case WidgetType.MULTI_PROPERTY_SELECTOR:
                properties = hint.choices() if hint.choices else []
                properties = properties + (self._manufacturer_properties or [])
                return MultiSelectWidget(properties, default=default)

            case WidgetType.AREA_SELECT:
                provider = None
                if beam_source := hint.beam_source:
                    if not scope.instances:
                        self._warn(
                            f"Field {fi.name!r} requests beam {beam_source!r} but "
                            "is not bound to live settings; the active beam is used."
                        )
                    else:

                        def provider():
                            return resolve_beam(scope, beam_source)

                return AreaSelectWidget(
                    microscope=self._microscope,
                    max_areas=hint.max_areas if hint.max_areas else None,
                    default=default,
                    beam_provider=provider,
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
        self, fi: FieldInfo, value: Any, on_change: OnChange, scope: BuildScope
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
                    model, settings=value, scope=scope, on_change=on_change
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
                    build_object=self._variant_builder(on_change, scope),
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
                    item_factory=self._make_item_factory(
                        item, on_change, scope.unaddressed()
                    ),
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

    def _variant_builder(
        self, on_change: OnChange, scope: BuildScope
    ) -> Callable[[type, list[FieldInfo] | None], ObjectWidget]:
        """
        Return the union widget's object factory, scoped to the union field.

        Args:
            on_change: The write-back threaded into the variant's fields.
            scope: Scope of the union field itself.

        Returns:
            A callable matching `DiscriminatedUnionWidget`'s `build_object`.
        """

        def build(cls: type, field_infos: list[FieldInfo] | None) -> ObjectWidget:
            self._forget_subtree(scope)
            obj = self._build_object(
                cls,
                settings=None,
                scope=scope,
                field_infos=field_infos,
                on_change=on_change,
            )
            if not scope.context.building:
                # a switch after the initial build: the rest of the form is
                # already registered, so only this subtree needs wiring
                self._flush_overlays(scope.context)
            return obj

        return build

    def _forget_subtree(self, scope: BuildScope) -> None:
        """
        Drop registry entries and overlay bindings strictly below `scope`.

        Args:
            scope: The subtree being replaced.
        """
        if (prefix := scope.dotted) is None:
            return

        context = scope.context
        dead = f"{prefix}."
        for path in [p for p in context.widgets if p.startswith(dead)]:
            del context.widgets[path]

        for binding in [
            b
            for b in context.bindings
            if b.area_path is not None and b.area_path.startswith(dead)
        ]:
            binding.deactivate()
            context.bindings.remove(binding)

    def _make_item_factory(
        self, item: FieldType, on_change: OnChange, scope: BuildScope
    ) -> Callable[[], BaseWidget]:
        """
        Return a factory building a widget for a single list element.

        The element's `on_change` is the same top-level write-back, so editing
        any item reconstructs and reassigns the whole list field. `scope` is
        unaddressed: list elements come and go, so their fields are not
        registered and can only be referenced as siblings.
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
                    self._build_object(
                        model, settings=None, scope=scope, on_change=on_change
                    )
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

    def _collect_overlays(
        self,
        infos: list[FieldInfo],
        widgets: dict[str, BaseWidget],
        scope: BuildScope,
    ) -> None:
        """
        Queue each area selector's overlays for wiring after the build.

        Wiring is deferred because an overlay source may live in a branch built
        later; only the flush pass sees the whole form.

        Args:
            infos: Field infos for the object currently being built.
            widgets: The built widgets for this object, keyed by field name.
            scope: The scope of the object currently being built.
        """
        for fi in infos:
            if fi.hint is None or not fi.hint.overlays:
                continue

            area = self._area_widget_of(widgets.get(fi.name))
            if area is None:
                self._warn(
                    f"Field {fi.name!r} declares area overlays but is not an "
                    "area selector; they will be ignored."
                )
                continue

            binding = OverlayBinding(
                area=area,
                area_path=scope.child(fi.name).dotted,
                field_name=fi.name,
                specs=tuple(fi.hint.overlays),
                scope=scope,
                siblings=widgets,
            )
            # a removed list item destroys its area without going through
            # _forget_subtree, so stop pushing when the widget dies
            area.destroyed.connect(binding.deactivate)
            scope.context.bindings.append(binding)

    def _flush_overlays(self, context: BuildContext) -> None:
        """
        Subscribe every unwired overlay binding to its sources and seed it.

        One callback per area selector drives all of that field's overlays, so
        each push carries a complete `OverlayData` per overlay and no partial
        state is observable when several sources feed one decoration.

        Args:
            context: The build whose bindings should be wired.
        """
        for binding in list(context.bindings):
            if binding.wired or not binding.active:
                continue
            binding.wired = True

            sources = self._overlay_sources(binding)
            if not sources:
                continue

            push = partial(self._push_overlays, binding)
            for source in sources:
                source.on_change(push)
            push()

    def _overlay_sources(self, binding: OverlayBinding) -> list[BaseWidget]:
        """
        Resolve a binding's source paths once, warning about the missing ones.

        Args:
            binding: The overlay binding being wired.

        Returns:
            The distinct source widgets to subscribe to, in declaration order.
        """
        found: dict[int, BaseWidget] = {}
        for spec in binding.specs:
            for _, path in spec.sources:
                source = self._resolve_source(binding, path)
                if source is None:
                    self._warn(
                        f"Overlay source {path!r} for field "
                        f"{binding.field_name!r} was not found in this form; "
                        f"{spec.kind.value} will not be drawn."
                    )
                    continue
                found.setdefault(id(source), source)
        return list(found.values())

    def _resolve_source(self, binding: OverlayBinding, path: str) -> BaseWidget | None:
        """
        Find the widget an overlay source path refers to.

        A bare name is looked up among the declaring object's own fields first,
        which keeps sibling references working inside list elements, where no
        addressable path exists. Otherwise the path is tried against each
        enclosing scope, innermost first.

        Args:
            binding: The overlay binding making the reference.
            path: Dotted path relative to the declaring object.

        Returns:
            The source widget, or None if the path matches nothing.
        """
        if "." not in path and (sibling := binding.siblings.get(path)) is not None:
            return sibling

        widgets = binding.scope.context.widgets
        for candidate in binding.scope.candidates(path):
            if (widget := widgets.get(candidate)) is not None:
                return widget
        return None

    def _push_overlays(self, binding: OverlayBinding) -> None:
        """
        Copy the current source values into the area selector's overlays.

        Source paths are re-resolved on every push rather than captured, so a
        rebuilt subtree cannot leave the overlay reading a discarded widget.

        Args:
            binding: The overlay binding to push.
        """
        if not binding.active:
            return

        overlays: list[tuple[AreaOverlay, OverlayData]] = []
        for spec in binding.specs:
            data: dict[str, Any] = {}
            for data_field, path in spec.sources:
                source = self._resolve_source(binding, path)
                if source is not None:
                    data[data_field] = source.get_value()
            overlays.append((spec.kind, OverlayData(**data)))

        binding.area.set_overlays(overlays)

    def _area_widget_of(self, widget: BaseWidget | None) -> AreaSelectWidget | None:
        """Return the `AreaSelectWidget` inside `widget`, unwrapping an optional."""
        if isinstance(widget, AreaSelectWidget):
            return widget
        if isinstance(widget, OptionalWidget):
            inner = widget.inner  # type: ignore
            if isinstance(inner, AreaSelectWidget):
                return inner
        return None

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
