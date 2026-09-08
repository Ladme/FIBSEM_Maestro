# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, TypeVar

from fibsem_maestro.core.beam_type import BeamType

if TYPE_CHECKING:
    from fibsem_maestro.gui.form_builder._overlay_binding import OverlayBinding
    from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget

T = TypeVar("T")


@dataclass
class BuildContext:
    """
    Mutable state shared by every scope within one form build.

    Attributes:
        widgets: Built field widgets by dotted path from the form root. Only
            addressable fields appear here (list elements are excluded).
        bindings: Overlay bindings collected during the build, wired by
            `FormBuilder._flush_overlays` once the whole tree exists.
        building: True while the initial build pass is running. Subtrees rebuilt
            later (union variant switches) flush their own overlays.
    """

    widgets: dict[str, BaseWidget] = field(default_factory=dict)
    bindings: list[OverlayBinding] = field(default_factory=list)
    building: bool = True


@dataclass(frozen=True)
class BuildScope:
    """
    The position of the object currently being built within the settings tree.

    Attributes:
        context: Per-build shared state (widget registry, overlay bindings).
        instances: Live settings instances, outermost first.
        path: Field names from the root, or None if this subtree is unaddressable.
    """

    context: BuildContext
    instances: tuple[Any, ...] = ()
    path: tuple[str, ...] | None = ()

    @property
    def dotted(self) -> str | None:
        """The dotted path of this scope, or None if it has no address."""
        return None if self.path is None else ".".join(self.path)

    def with_instance(self, settings: Any | None) -> BuildScope:
        """Return this scope with `settings` appended as the innermost instance."""
        if settings is None:
            return self
        return replace(self, instances=(*self.instances, settings))

    def child(self, name: str) -> BuildScope:
        """Return the scope of field `name` within this object."""
        if self.path is None:
            return self
        return replace(self, path=(*self.path, name))

    def unaddressed(self) -> BuildScope:
        """Return this scope with its address dropped (for list elements)."""
        return replace(self, path=None)

    def candidates(self, path: str) -> tuple[str, ...]:
        """
        Absolute candidate paths for a reference made from this scope.

        Args:
            path: Dotted path relative to this scope, e.g. `"milling_depth"` or `"milling.milling_depth"`.

        Returns:
            Candidate absolute paths, innermost scope first, ending at the root.
            An unaddressed scope can only offer the root-relative path.
        """
        if self.path is None:
            return (path,)
        prefixes = (self.path[:i] for i in range(len(self.path), -1, -1))
        return tuple(".".join((*prefix, path)) for prefix in prefixes)

    def value(self, path: str, kind: type[T]) -> T | None:
        """
        Resolve a dotted path against the live instances, innermost first.

        Args:
            path: Dotted attribute path relative to a chain member.
            kind: Required type of the resolved value.

        Returns:
            The first value of type `kind` found, or None if no enclosing
            instance defines one.
        """
        parts = path.split(".")
        for obj in reversed(self.instances):
            current: Any = obj
            for part in parts:
                current = getattr(current, part, None)
                if current is None:
                    break
            if isinstance(current, kind):
                return current
        return None


def resolve_beam(scope: BuildScope, path: str) -> BeamType | None:
    """
    Look up a beam on the innermost enclosing settings object that defines it.

    Args:
        scope: The scope of the field requesting a beam.
        path: Dotted attribute path relative to a chain member, e.g. `"beam_type"`
            or `"imaging.beam_type"`.

    Returns:
        The first non-None beam found, or None if no ancestor defines one.
    """
    return scope.value(path, BeamType)
