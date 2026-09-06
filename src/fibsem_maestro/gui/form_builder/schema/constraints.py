# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from dataclasses import dataclass


@dataclass(frozen=True)
class Bound:
    """
    A single numeric bound.

    Attributes:
        value: The bound value.
        exclusive: True for strict bounds (`gt` / `lt`), False for
            inclusive bounds (`ge` / `le`).
    """

    value: float
    exclusive: bool


@dataclass(frozen=True)
class NumericBounds:
    """Lower and/or upper numeric constraints on a field.

    Invariant: at least one of `minimum` / `maximum` is non-`None`. A
    field with no constraints is represented by `NumericBounds` being
    `None`, never by an all-`None` instance.

    Attributes:
        minimum: The lower bound, or `None` if unconstrained below.
        maximum: The upper bound, or `None` if unconstrained above.
    """

    minimum: Bound | None = None
    maximum: Bound | None = None


def extract_bounds(extras: tuple) -> NumericBounds | None:
    """
    Pull `gt` / `ge` / `lt` / `le` constraints out of metadata.
    """
    minimum: Bound | None = None
    maximum: Bound | None = None

    for arg in extras:
        gt, ge = getattr(arg, "gt", None), getattr(arg, "ge", None)
        lt, le = getattr(arg, "lt", None), getattr(arg, "le", None)
        # gt/lt are exclusive; ge/le inclusive. Later assignment wins.
        if gt is not None:
            minimum = Bound(float(gt), exclusive=True)
        if ge is not None:
            minimum = Bound(float(ge), exclusive=False)
        if lt is not None:
            maximum = Bound(float(lt), exclusive=True)
        if le is not None:
            maximum = Bound(float(le), exclusive=False)

        # some carriers (e.g. pydantic FieldInfo) nest the real constraints
        nested = getattr(arg, "metadata", None)
        if nested:
            inner = extract_bounds(tuple(nested))
            if inner is not None:
                minimum = inner.minimum or minimum
                maximum = inner.maximum or maximum
    if minimum is None and maximum is None:
        return None
    return NumericBounds(minimum, maximum)
