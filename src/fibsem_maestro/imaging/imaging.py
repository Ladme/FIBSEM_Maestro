# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import contextvars
import threading

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
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
from fibsem_maestro.store.props.props_store import PropsStore
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
    def external_props(self) -> GlobalProperties:
        """External properties to use for this imaging action."""
        return self._settings.external_props

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

        if state.image_sharpness is None and self.settings.criterion is not None:
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
                f"Skipping {self.name} for slice {self._ctx.slice}."
            )
            # even if imaging is skipped, we need to write properties for the next slice
            self.write_properties(self.read_properties(), self._ctx.props_store.next)
            return

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
        self.collect_and_write_properties(self._ctx.props_store.next)

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

    @with_logging_context
    def collect_and_write_properties(
        self,
        store: PropsStore | None = None,
    ) -> None:
        """
        Collect and save the relevant properties of the microscope.

        Args:
            store: Store to write properties to. If `None`, the current slice's store is used.
        """
        store = store or self._ctx.props_store
        self._ctx.text_logger.debug("Saving microscope properties for imaging.")

        self._microscope.set_beam(self._settings.beam_type)

        # set external microscope properties such as scanning area or bit depth
        with self._microscope.set_temporary_properties(self.external_props):
            match self._settings.resolution_mode:
                case StandardResolution():
                    pass
                case ExtendedResolution() as mode:
                    self._set_extended_resolution_props(
                        mode.pixel_size,
                    )

            # collect the microscope properties
            props = self._microscope.collect_properties(
                self._settings.properties_to_collect
            )

            # save the properties to a file
            store.write("props.yaml", props)

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

    def _set_extended_resolution_props(self, new_pixel_size: float) -> None:
        """
        Configure the beam for extended resolution imaging.

        When a non-full-frame scanning area is configured, shifts the beam
        to the centre of that area and resizes the field of view to match its physical dimensions.

        The scanning area is always reset to full frame after the adjustment,
        since the beam shift and FOV take over the role of area selection in
        extended resolution mode. The pixel size is always updated to
        `new_pixel_size`, regardless of whether a scanning area is configured.

        Args:
            new_pixel_size: The target pixel size in nanometers.
        """
        # get external properties for the relevant beam
        props = (
            self._settings.external_props.electron_beam
            if self._settings.beam_type == BeamType.ELECTRON
            else self._settings.external_props.ion_beam
        )

        # image only the scanning area
        if (
            props is not None
            and (area := props.scanning_area) is not None
            and not area.is_full_frame()
            and not self._scanning_area_selected
        ):
            self._ctx.text_logger.debug(
                "Setting scanning area using extended resolution."
            )

            # shift the beam to the center of the scanning area
            img_res = self._microscope.beam.resolution
            pixel_size = self._microscope.beam.pixel_size
            area_nm = area.to_nanometers(img_res, pixel_size)
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
