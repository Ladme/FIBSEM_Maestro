# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


import contextvars
import threading
from contextlib import ExitStack, nullcontext
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
    scanning_area_selected: bool = False
    image_sharpness: float | None = None


@ACTION_REGISTRY.register("imaging")
class Imaging(Action[ImagingSettings, ImagingState]):
    """
    Orchestrates a single image acquisition cycle on the electron microscope.
    """

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

        # was scanning area selected using extended resolution
        # necessary to avoid shrinking the selected area in subsequent imagings
        self._scanning_area_selected = False

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
            scanning_area_selected=self._scanning_area_selected,
            image_sharpness=self._image_sharpness,
        )

    def set_state(self, state: ImagingState) -> None:
        self._scanning_area_selected = state.scanning_area_selected
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
                image = self._ctx.frame_store.read()
            except FileNotFoundError:
                self._ctx.text_logger.warning(
                    f"Restoring state of '{self.name}': frame for slice {self._ctx.slice} not found, falling back to slice {self._ctx.slice - 1}."
                )
                # if this fails, fall back to the previous slice
                # this should only happen if the image successfully completes the execution,
                # but the background thread does not finish the calculation before interrupt
                image = self._ctx.frame_store.at(self._ctx.slice - 1).read()
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
        props = self.collect_properties()
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

        Overrides the default implementation.

        Args:
            store: Store to write properties to. If `None`, the current slice's store is used.

        Returns:
            The collected properties.
        """
        self._ctx.text_logger.debug(
            f"Collecting microscope properties for {self.name}."
        )

        # get scanning area from the settings
        try:
            scanning_area = self._settings.scanning_area[0]
        except IndexError:
            scanning_area = None

        if scanning_area:
            self._ctx.text_logger.debug(
                f"Scanning area specified in FIBSEM Maestro: {scanning_area}."
            )

        # scanning area from the settings should override the scanning area set in the microscope's GUI
        # when using extended resolution, the scanning area must always be set via scanning_area property in settings
        with (
            self._microscope.set_temporary_beam_property(
                "scanning_area",
                scanning_area,
                self._settings.beam_type,
                # only set the scanning area if it is not None
            )
            if scanning_area is not None
            else nullcontext(),
        ):
            match self._settings.resolution_mode:
                case StandardResolution():
                    pass
                case ExtendedResolution() as mode:
                    self._set_extended_resolution_props(
                        scanning_area or self._microscope.beam.scanning_area,
                        mode.pixel_size,
                    )

            # collect the microscope properties
            return self._microscope.collect_properties(
                self._settings.properties_to_collect
            )

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

    def _set_extended_resolution_props(
        self, scanning_area: RelativeArea, new_pixel_size: float
    ) -> None:
        """
        Configure the beam for extended resolution imaging.

        When a non-full-frame scanning area is configured, shifts the beam
        to the centre of that area and resizes the field of view to match its physical dimensions.

        The scanning area is always reset to full frame after the adjustment,
        since the beam shift and FOV take over the role of area selection in
        extended resolution mode. The pixel size is always updated to
        `new_pixel_size`, regardless of whether a scanning area is configured.

        Args:
            scanning_area: The scanning area to image.
            new_pixel_size: The target pixel size in nanometers.
        """
        # image only the scanning area
        if not scanning_area.is_full_frame() and not self._scanning_area_selected:
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
            self._microscope.beam.horizontal_field_width = area_nm.width
            self._microscope.beam.vertical_field_width = area_nm.height

            self._scanning_area_selected = True

        # always set scanning area to full frame
        self._microscope.beam.scanning_area = RelativeArea.full()

        # set resolution based on the new pixel size
        # this is done even if scanning area is not specified
        self._microscope.beam.pixel_size = new_pixel_size

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
