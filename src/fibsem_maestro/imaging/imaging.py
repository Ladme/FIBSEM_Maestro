# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import contextvars
import threading
from contextlib import ExitStack
from pathlib import Path

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.format import ImageFormat
from fibsem_maestro.core.image import Image
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.imaging.error import ImagingError
from fibsem_maestro.logging.logging import with_logging_context
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.imaging_settings import (
    ExtendedResolution,
    ImagingSettings,
    StandardResolution,
)
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.workflow.actions import Actions


class ImagingState(ActionState):
    image_sharpness: float | None = None


@ACTION_REGISTRY.register("imaging")
class Imaging(Action[ImagingSettings, ImagingState]):
    """
    Orchestrates a single image acquisition cycle on the electron microscope.
    """

    # beam properties altered by `_set_extended_resolution_props`
    # pixel size and vertical field width are derived from horizontal field width and
    # resolution, so restoring those two restores them as well
    _EXTENDED_RESOLUTION_STATE: tuple[str, ...] = (
        "beam_shift",
        "horizontal_field_width",
        "resolution",
        "scanning_area",
    )

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: ImagingSettings,
        ctx: ActionContext,
        actions: Actions,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._ctx = ctx
        self._actions = actions

        # sharpness of the acquired image
        self._image_sharpness: float | None = None
        self._sharpness_thread: threading.Thread | None = None

        # save the last acquired image
        self._last_acquired_image: Image | None = None

    @classmethod
    def settings_cls(cls) -> type[ImagingSettings]:
        return ImagingSettings

    @classmethod
    def state_cls(cls) -> type[ImagingState]:
        return ImagingState

    @property
    def name(self) -> str:
        """Human-readable identifier for this imaging instance."""
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def beam_type(self) -> BeamType | None:
        """Beam type used for acquisition, either electron or ion."""
        return self._settings.beam_type

    @property
    def props_to_collect(self) -> PropertyNames:
        """Names of microscope properties relevant for the image acquisition."""
        return self._settings.properties_to_collect

    @property
    def microscope(self) -> Microscope:
        """The microscope instance used for the imaging."""
        return self._microscope

    @property
    def settings(self) -> ImagingSettings:
        return self._settings

    @property
    def ctx(self) -> ActionContext:
        return self._ctx

    @property
    def state(self) -> ImagingState:
        return ImagingState(
            image_sharpness=self._image_sharpness,
        )

    def set_state(self, state: ImagingState) -> None:
        self._image_sharpness = state.image_sharpness

        if (
            # skip if the acquisition hasn't started yet
            self._ctx.slice != 0
            and state.image_sharpness is None
            and self.settings.criterion is not None
        ):
            self._ctx.text_logger.warning(
                f"Restoring state of '{self.name}': image sharpness not computed, recovering from frame captured for slice {self._ctx.slice}."
            )
            # sharpness was not computed before the interrupt - recover it now
            # by loading the persisted frame and computing synchronously
            try:
                # try to load the frame for the current slice
                image = self._ctx.frame_store.read(self._microscope.provenance)
            except FileNotFoundError:
                self._ctx.text_logger.warning(
                    f"Restoring state of '{self.name}': frame for slice {self._ctx.slice} not found, falling back to slice {self._ctx.slice - 1}."
                )
                # if this fails, fall back to the previous slice
                # this should only happen if the image successfully completes the execution,
                # but the background thread does not finish the calculation before interrupt
                image = self._ctx.frame_store.at(self._ctx.slice - 1).read(
                    self._microscope.provenance
                )
            self._last_acquired_image = image
            self._calculate_sharpness(image, self._ctx.current_view)

    @property
    def last_acquired_image(self) -> Image | None:
        """Get the last image acquired by this imaging."""
        return self._last_acquired_image

    @with_logging_context
    def execute(self) -> None:
        """
        Execute the full image acquisition pipeline for the current slice.

        Loads stored microscope properties and applies them to the beam,
        acquires a frame and persists it via the frame store, writes updated
        properties to the next slice's store, and optionally launches a
        background thread to evaluate image sharpness.

        Call `wait_for_sharpness` after this method to block until the
        sharpness result is available.

        Raises:
            ImagingError: If a frame for the current slice already exists in the frame store.
        """
        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (self._ctx.slice - 1) % self._settings.execution_frequency != 0
        ):
            self._ctx.text_logger.info(
                f"Skipping '{self.name}' for slice {self._ctx.slice}."
            )
            # even if imaging is skipped, we need to write properties for the next slice
            self.propagate_to_next()
            return

        self._ctx.text_logger.info(
            f"Started '{self.name}' for slice {self._ctx.slice}."
        )

        # set the properties of the microscope
        self.read_and_set_properties()

        # make sure that the image for the current slice does not exist
        self._ctx.frame_store.raise_if_exists(
            ImagingError,
            f"Frame for slice {self._ctx.slice} for action '{self.name}' already exists.",
        )

        # grab the frame and save it
        self._last_acquired_image = self._microscope.beam.grab_frame(
            self._ctx.frame_store
        )

        # update the saved microscope properties for the next frame
        # if we are in extended resolution, we skip setting up the geometry of the captured area
        # since that would actually mess it up
        props = self._collect_properties_in_current_geometry()
        self.write_properties(props, self._ctx.props_store.next)

        # calculate image sharpness in a separate thread
        self._image_sharpness = None
        if self._settings.criterion is not None:
            # capture the current logging context to use in the thread
            # this is done so that the logs from the sharpness calculation
            # are logged to the correct slice
            current_view = self._ctx.current_view
            ctx_snapshot = contextvars.copy_context()
            self._sharpness_thread = threading.Thread(
                target=ctx_snapshot.run,
                args=(
                    self._calculate_sharpness,
                    self._last_acquired_image,
                    current_view,
                ),
            )
            self._sharpness_thread.start()
        else:
            self._ctx.text_logger.debug(
                f"Criterion is not configured for {self.name}. Image sharpness will not be calculated."
            )

        self._ctx.text_logger.info(
            f"Completed '{self.name}' for slice {self._ctx.slice}."
        )

    @with_logging_context
    def test(self) -> None:
        """
        Acquire a single test frame and save it alongside the slice frames.

        If persisted properties exist they are read and applied to the
        microscope; otherwise the external action properties and the first
        configured scanning area are applied temporarily for the duration of
        the acquisition.
        """
        self._ctx.text_logger.info(f"Started test for {self.name}.")

        with ExitStack() as stack:
            if self._ctx.props_store.exists("props.yaml"):
                self._ctx.text_logger.info("Loading saved microscope properties.")
                self.read_and_set_properties()
            else:
                self._ctx.text_logger.info("No saved microscope properties found.")
                # the external action properties and the scanning area from
                # settings must be applied to the microscope only for the
                # duration of this acquisition.
                if (scanning_area := self._first_scanning_area()) is not None:
                    stack.enter_context(
                        self._microscope.set_temporary_beam_property(
                            "scanning_area",
                            scanning_area,
                            self._settings.beam_type,
                        )
                    )

            output_path = self._grab_test_frame()

        self._ctx.text_logger.info(
            f"Completed test for {self.name}. Acquired image saved as {output_path}."
        )

    def _first_scanning_area(self) -> RelativeArea | None:
        """
        Return the configured scanning area, if any.

        Returns:
            The first scanning area from the settings,
            or `None` when no scanning area is configured.
        """
        return next(iter(self._settings.scanning_area), None)

    def _grab_test_frame(self) -> Path:
        """
        Grab a frame and save it with the `.test.tif` suffix.

        The frame is stored manually rather than through the frame store so
        that it does not block acquisition of further images for the current
        slice.

        Returns:
            The path the acquired image was written to.
        """
        image = self._microscope.beam.grab_frame()
        output_path = Path(str(self._ctx.frame_store.path())).with_suffix(".test.tif")
        image.save(output_path, ImageFormat.TIF)
        return output_path

    @with_logging_context
    def collect_properties(self) -> GlobalProperties:
        """
        Collect the relevant properties of the microscope.

        Overrides the default implementation. In extended resolution mode the
        geometry is established before collecting, so that the collected
        properties describe the region to image rather than the current frame.

        This is the entry point for a manual collection, after the user has set
        the microscope up by hand. `execute` uses
        `_collect_properties_in_current_geometry` instead, since the properties
        it reads already carry the geometry.

        Returns:
            The collected properties.
        """
        return self._collect(apply_extended_geometry=True)

    def _collect_properties_in_current_geometry(self) -> GlobalProperties:
        """
        Collect the relevant properties without altering the microscope geometry.

        In extended resolution mode the beam shift is additive and the field of
        view shrink absolute, so the geometry is established once and then
        carried in the collected properties. Re-applying it on every slice would
        compound the shift and shrink the field of view further each time.

        Returns:
            The collected properties.
        """
        return self._collect(apply_extended_geometry=False)

    def _collect(self, apply_extended_geometry: bool) -> GlobalProperties:
        """
        Dispatch property collection according to the configured resolution mode.

        Args:
            apply_extended_geometry: Whether to establish the extended
                resolution geometry before collecting. Ignored in standard
                resolution mode, which never alters the geometry.

        Returns:
            The collected properties.
        """
        self._ctx.text_logger.debug(
            f"Collecting microscope properties for {self.name}."
        )

        scanning_area = self._first_scanning_area()
        if scanning_area is not None:
            self._ctx.text_logger.debug(
                f"Scanning area specified in FIBSEM Maestro: {scanning_area}."
            )

        match self._settings.resolution_mode:
            case StandardResolution():
                return self._collect_standard_properties(scanning_area)
            case ExtendedResolution() as mode:
                return self._collect_extended_properties(
                    scanning_area, mode, apply_extended_geometry
                )

    def _collect_standard_properties(
        self, scanning_area: RelativeArea | None
    ) -> GlobalProperties:
        """
        Collect properties in standard resolution mode.

        The microscope geometry is not altered. The scanning area configured in
        FIBSEM Maestro replaces the one read from the instrument, so that it is
        applied on the next slice; the remaining scan parameters are recorded as
        read, whatever area they were set for.

        Args:
            scanning_area: Scanning area from the settings, or `None` when none
                is configured.

        Returns:
            The collected properties.
        """
        # Autoscript supports only a fixed set of resolutions for its beams, so
        # extended resolution is emulated outside the instrument: the beam
        # control holds the requested value and shadows what Autoscript reports;
        # standard mode must clear that emulation before collecting, or it would
        # record the extended resolution and carry it into the next slice; other
        # vendors may set arbitrary resolutions directly, in which case this is a no-op.
        self._microscope.beam.clear_extended_resolution()

        props = self._microscope.collect_properties(
            self._settings.properties_to_collect
        )

        if scanning_area is not None:
            props.set_property("scanning_area", scanning_area, self._settings.beam_type)

        return props

    def _collect_extended_properties(
        self,
        scanning_area: RelativeArea | None,
        mode: ExtendedResolution,
        apply_geometry: bool,
    ) -> GlobalProperties:
        """
        Collect properties in extended resolution mode.

        When `apply_geometry` is True, the extended resolution geometry is
        established, the resulting properties collected, and the microscope
        restored to the state it was in on entry. Otherwise the properties are
        collected as they stand: within a run they already carry the geometry.

        Args:
            scanning_area: Scanning area from the settings, or `None` to fall
                back to the one currently set on the instrument.
            mode: The extended resolution settings.
            apply_geometry: Whether to establish the geometry before collecting.

        Returns:
            The collected properties.
        """
        if not apply_geometry:
            return self._microscope.collect_properties(
                self._settings.properties_to_collect
            )

        with ExitStack() as stack:
            for name in self._EXTENDED_RESOLUTION_STATE:
                stack.enter_context(
                    self._microscope.set_temporary_beam_property(
                        name,
                        getattr(self._microscope.beam, name),
                        self._settings.beam_type,
                    )
                )

            self._set_extended_resolution_props(
                scanning_area
                if scanning_area is not None
                else self._microscope.beam.scanning_area,
                mode.pixel_size,
            )

            props = self._microscope.collect_properties(
                self._settings.properties_to_collect
            )

        # extended resolution replaces area selection with beam shift + FOV
        props.set_property(
            "scanning_area", RelativeArea.full(), self._settings.beam_type
        )

        self._microscope.beam.clear_extended_resolution()

        return props

    def _set_extended_resolution_props(
        self, scanning_area: RelativeArea, new_pixel_size: float
    ) -> None:
        """
        Configure the beam for extended resolution imaging.

        When a non-full-frame scanning area is configured, shifts the beam to
        the center of that area and resizes the field of view to match its
        physical dimensions. The pixel size is always updated to
        `new_pixel_size`, regardless of whether a scanning area is configured.

        The beam shift is additive and the field of view shrink absolute, so
        this must be called only when the geometry is being established, not on
        every collection.

        The scanning area is deliberately left as it is: the caller collects the
        properties before restoring it, so that the scan parameters Autoscript
        maintains separately for a reduced area are preserved. Restoring the
        altered beam state is the caller's responsibility.

        Args:
            scanning_area: The scanning area to image, relative to the full frame.
            new_pixel_size: The target pixel size in nanometers.
        """
        # image only the scanning area
        if not scanning_area.is_full_frame():
            self._ctx.text_logger.debug(
                "Setting scanning area using extended resolution."
            )

            # shift the beam to the center of the scanning area
            img_res = self._microscope.beam.resolution
            pixel_size = self._microscope.beam.pixel_size
            area_nm = scanning_area.to_nanometers(img_res, pixel_size)
            image_to_beam_shift = self._microscope.beam.image_to_beam_shift

            shift = BeamShift(
                image_to_beam_shift[0]
                * (
                    area_nm.origin.x
                    - (img_res.width // 2 * pixel_size)
                    + area_nm.width / 2.0
                ),
                image_to_beam_shift[1]
                * (
                    area_nm.origin.y
                    - (img_res.height // 2 * pixel_size)
                    + area_nm.height / 2.0
                ),
            )

            self._microscope.add_beam_shift_with_verification(shift)

            # set the FOV to the scanning area
            # HFW must be set before VFW: the VFW setter derives the new
            # resolution from the pixel size that setting HFW has just changed
            self._microscope.beam.horizontal_field_width = area_nm.width
            self._microscope.beam.vertical_field_width = area_nm.height

        # set resolution based on the new pixel size
        # this is done even if scanning area is not specified
        self._microscope.beam.pixel_size = new_pixel_size

    def wait_for_sharpness(self) -> float | None:
        """
        Block until the background sharpness calculation finishes.

        Returns:
            The calculated sharpness value, or `None` if no criterion is
            configured or the calculation failed.
        """
        if self._sharpness_thread is not None:
            self._sharpness_thread.join()
        return self._image_sharpness

    def wait_for_background_threads(self) -> None:
        self.wait_for_sharpness()

    def _calculate_sharpness(self, image: Image, view: SliceView) -> None:
        """
        Evaluate image sharpness on a background thread.

        Computes the sharpness score via the configured criterion and stores
        the result in `_image_sharpness`. Any exception raised during
        calculation is caught and logged as a warning so that a failure cannot
        crash the background thread.

        Args:
            image: The image to evaluate.
            view: The slice view to use for logging.
        """
        assert self._settings.criterion is not None

        # get logger for the slice corresponding to the provided view
        text_logger = self._ctx.text_logger.at(view.slice_index)
        image_logger = self._ctx.image_logger.at(view.slice_index)

        criterion = Criterion(
            self._settings.criterion,
            text_logger.derive("criterion"),
            image_logger,
        )

        try:
            self._image_sharpness = criterion.calculate_sharpness(image)
            text_logger.debug(f"Image sharpness: {self._image_sharpness}.")
        except Exception as e:
            text_logger.warning(f"Could not calculate image sharpness: {e}")
