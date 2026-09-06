# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


import dataclasses
from typing import Any, get_args, get_origin

from pydantic import BaseModel


def is_dataclass_type(t: Any) -> bool:
    """True for dataclass classes and Pydantic BaseModel subclasses."""
    return dataclasses.is_dataclass(t) and isinstance(t, type)


def is_pydantic_model(cls: Any) -> bool:
    """True if `cls` is a Pydantic `BaseModel` subclass."""
    return isinstance(cls, type) and issubclass(cls, BaseModel)


def is_model(t: Any) -> bool:
    """True if `t` is either a dataclass or a Pydantic model."""
    return is_dataclass_type(t) or is_pydantic_model(t)


def is_float_tuple(t: Any) -> bool:
    """
    True for a fixed-length, all-float tuple such as `tuple[float, float]`.

    A bare, unparameterised `tuple` is excluded.
    """
    if get_origin(t) is not tuple:
        return False
    args = get_args(t)
    return len(args) > 0 and all(a is float for a in args)
