# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import logging
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SliceContext:
    """
    Tracks the current slice index for slice-aware logging.
    """

    current_slice: int | None = None

    def increment(self) -> None:
        """
        Advance the slice counter by one.

        If `current_slice` is `None`, the first call initializes it
        to `0`. Otherwise, it increments the existing slice value.
        """
        if self.current_slice is None:
            self.current_slice = 0
        else:
            self.current_slice += 1


@dataclass
class LogContext:
    """
    Provides slice-aware and centralized logging file paths.

    This context binds together the root directory, the slice index,
    and the desired log level. Infrastructure loggers use this context
    to determine where log files and image outputs should be written.

    Attributes:
        root_dir (Path): Base directory for all logging output.
            May contain slice directories or centralized logs.
        slice_ctx (SliceContext): Holds the current slice number.
            Determines whether logging is centralized or slice-based.
        log_level (int): Logging level used by infrastructure loggers
            (e.g., `logging.INFO`, `logging.DEBUG`).
    """

    root_dir: Path
    slice_ctx: SliceContext
    log_level: int = logging.INFO

    def slice_dir(self, slice: int | None = None) -> Path:
        """
        Return the directory used for slice-specific or central logging.

        The directory is created if it does not already exist.

        Args:
            slice (int | None): The slice for which the directory should be returned.
                                Assumes current slice if `None`.

        Returns:
            Path: The directory where log files and images should be written.
        """
        if slice is not None:
            d = self.root_dir / f"slice_{slice:04d}"
        elif self.slice_ctx.current_slice is None:
            d = self.root_dir
        else:
            d = self.root_dir / f"slice_{self.slice_ctx.current_slice:04d}"

        d.mkdir(parents=True, exist_ok=True)
        return d

    def images(self) -> Path:
        """
        Return the directory where image logs should be written.

        Returns:
            Path: Directory for image output.
        """
        d = self.slice_dir() / "images"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def logs(self) -> Path:
        """
        Return the log file path for the current slice.

        Returns:
            Path: Path to the active log file.
        """
        return self.slice_dir() / "app.log"

    def central_logs(self) -> Path:
        """
        Return the centralized log file path.

        Returns:
            Path: Path to the centralized log file.
        """
        self.root_dir.mkdir(parents=True, exist_ok=True)
        return self.root_dir / "app.log"
