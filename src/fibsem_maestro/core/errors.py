# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


class AutoscriptNotAvailableError(ImportError):
    """Raised when the Autoscript library is required but not linked."""

    def __init__(self) -> None:
        super().__init__("Autoscript is not available.")
