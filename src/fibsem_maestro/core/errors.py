# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


class AutoscriptNotAvailableError(ImportError):
    """Raised when the Autoscript library is required but not linked."""

    def __init__(self) -> None:
        super().__init__(
            "Autoscript is required to use `from_autoscript()`. "
            "Run `uv run src/link_autoscript.py` to link it."
        )
