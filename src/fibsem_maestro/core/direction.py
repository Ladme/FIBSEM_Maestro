# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from enum import Enum


class Direction(str, Enum):
    """
    Represents direction in the image.
    """

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
