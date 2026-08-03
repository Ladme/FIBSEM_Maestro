# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

import threading


class SliceCounter:
    """
    Thread-safe counter tracking the current slice index for one action.

    Each action owns one `SliceCounter`. Calling `advance` atomically increments
    the index and returns the new value.

    Args:
        initial: Starting value. Defaults to `0` so that the first call to `advance` yields slice `1`.
    """

    def __init__(self, initial: int = 0) -> None:
        self._value = initial
        self._lock = threading.Lock()

    @property
    def current(self) -> int:
        """
        The current slice index.

        Returns:
            The most recently assigned slice index.
        """
        return self._value

    def advance(self) -> int:
        """
        Increment the slice index and return the new value.

        Thread-safe: concurrent callers will each receive a distinct index.

        Returns:
            The new slice index after incrementing.
        """
        with self._lock:
            self._value += 1
            return self._value
