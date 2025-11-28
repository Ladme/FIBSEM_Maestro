# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pydantic import Field
from typing import Annotated, Literal, Union

from pydantic import BaseModel


class BasicMode(BaseModel):
    type: Literal["basic"] = "basic"
    get_best_tile: bool = False


class MapMode(BaseModel):
    type: Literal["map"] = "map"
    get_best_tile: bool = False


class MaskMode(BaseModel):
    type: Literal["mask"] = "mask"
    mask_name: str


CriterionMode = Annotated[BasicMode | MapMode | MaskMode, Field(discriminator="type")]
