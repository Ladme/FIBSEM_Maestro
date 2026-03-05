# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SliceView:
    """
    Read/write accessor for a single slice's output paths.

    All directory-returning methods create the directory on disk before
    returning its path.

    Attributes:
        root_dir: The root output directory shared across all slices.
        slice_index: The slice this view addresses, or `None` for the
            root directory (used before the first slice is started).
    """

    root_dir: Path
    slice_index: int | None

    def _subdir(self, *parts: str) -> Path:
        """
        Return a subdirectory of this slice's directory, creating it first.

        Args:
            *parts: Path components appended to `dir`.

        Returns:
            The resolved, existing directory path.
        """
        d = self.dir().joinpath(*parts)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def dir(self) -> Path:
        """
        Return the top-level directory for this slice, creating it first.

        Returns:
            `root_dir / slice_NNNN` when `slice_index` is set,
            otherwise `root_dir` itself.
        """
        d = (
            self.root_dir / f"slice_{self.slice_index:04d}"
            if self.slice_index is not None
            else self.root_dir
        )
        d.mkdir(parents=True, exist_ok=True)
        return d

    def images(self) -> Path:
        """
        Return the directory for image output, creating it first.

        Returns:
            Path to the `images` subdirectory of this slice.
        """
        return self._subdir("images")

    def props(self) -> Path:
        """
        Return the directory for microscope property files, creating it first.

        Returns:
            Path to the `props` subdirectory of this slice.
        """
        return self._subdir("props")

    def custom(self, directory: str) -> Path:
        """
        Return a custom-named subdirectory for this slice, creating it first.

        Args:
            directory: Name of the subdirectory to create beneath this
                slice's directory.

        Returns:
            Path to the requested subdirectory.
        """
        return self._subdir(directory)

    def logs(self) -> Path:
        """
        Return the log file path for this slice.

        The parent directory is created if it does not already exist, but
        the log file itself is not created.

        Returns:
            Path to `app.log` inside this slice's directory.
        """
        return self.dir() / "app.log"


@dataclass
class SliceContext:
    """
    Tracks the active slice and vends `SliceView` accessors.

    The common case — reading or writing files for the current slice —
    is available directly on this object via convenience methods that
    delegate to `current`. For cross-slice access, use
    `at` or `root` to obtain an explicit `SliceView`.

    Attributes:
        root_dir: The root output directory shared across all slices.
        current_slice: Index of the active slice, or `None` if no slicing is defined.
    """

    root_dir: Path
    current_slice: int | None = None

    def increment(self) -> None:
        """
        Advance the slice counter by one.

        If `current_slice` is None, does nothing. Otherwise incremenets the current slice.
        """
        if self.current_slice is None:
            return

        self.current_slice += 1

    @property
    def current(self) -> SliceView:
        """
        Return a `SliceView` for the active slice.

        When `current_slice` is `None`, this is equivalent to `root`.

        Returns:
            A `SliceView` addressing the current slice.
        """
        return SliceView(root_dir=self.root_dir, slice_index=self.current_slice)

    @property
    def next(self) -> SliceView:
        """
        Return a `SliceView` for the next slice.

        When `current_slice` is None, this is equivalent to `root`.

        Returns:
            A `SliceView` addressing the slice following the current one.
        """
        return SliceView(
            root_dir=self.root_dir,
            slice_index=self.current_slice + 1
            if self.current_slice is not None
            else None,
        )

    @property
    def root(self) -> SliceView:
        """
        Return a `SliceView` for the root directory.

        Useful for writing files that belong to the run as a whole rather
        than to any individual slice.

        Returns:
            A `SliceView` with `slice_index=None`.
        """
        return SliceView(root_dir=self.root_dir, slice_index=None)

    def at(self, slice_index: int) -> SliceView:
        """
        Return a `SliceView` for an arbitrary slice.

        Args:
            slice_index: Index of the slice to address.

        Returns:
            A `SliceView` addressing the requested slice.
        """
        return SliceView(root_dir=self.root_dir, slice_index=slice_index)

    def dir(self) -> Path:
        """Return the directory for the current slice."""
        return self.current.dir()

    def images(self) -> Path:
        """Return the images directory for the current slice."""
        return self.current.images()

    def props(self) -> Path:
        """Return the props directory for the current slice."""
        return self.current.props()

    def custom(self, directory: str) -> Path:
        """Return a custom subdirectory for the current slice."""
        return self.current.custom(directory)

    def logs(self) -> Path:
        """Return the log file path for the current slice."""
        return self.current.logs()
