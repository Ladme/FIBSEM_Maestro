# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any


class WidgetWrapper:
    """
    Base interface for field widgets.
    """

    def get_value(self) -> Any:
        raise NotImplementedError(
            f"get_value is not implemented for {self.__class__.__name__}"
        )

    def set_value(self, value: Any) -> None:
        raise NotImplementedError(
            f"set_value is not implemented for {self.__class__.__name__}"
        )

    def set_read_only(self, read_only: bool) -> None:
        raise NotImplementedError(
            f"set_read_only is not implemented for {self.__class__.__name__}"
        )
