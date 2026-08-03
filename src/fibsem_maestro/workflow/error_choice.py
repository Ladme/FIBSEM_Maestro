# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from enum import Enum


class ErrorChoice(Enum):
    RETRY = "retry"
    SKIP = "skip"
    TERMINATE = "terminate"
