# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from fibsem_maestro.action.action import Action
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.area import NMArea
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.direction import Direction
from fibsem_maestro.logging.logging import with_logging_context
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.milling.error import MillingError
from fibsem_maestro.settings.milling_settings import MillingSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.actions import Actions


class MillingState(ActionState):
    milling_slice: NMArea | None


@ACTION_REGISTRY.register("milling")
class Milling(Action[MillingSettings, MillingState]):
    """
    Performs focused ion beam milling one slice at a time.

    Executes a rectangular milling pattern at a configurable depth and
    direction, advancing the milling area by the configured slice distance
    after each step.

    Args:
        name: Human-readable identifier for this milling instance.
        microscope: Interface to the electron microscope.
        settings: Milling configuration.
        props_store: Store for reading and writing microscope properties.
        text_store: Store for reading and writing text data.
        txt_log: Logger for diagnostic and status messages.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: MillingSettings,
        ctx: ActionContext,
        actions: Actions,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._ctx = ctx
        self._actions = actions

        self._current_milling_slice: NMArea | None = None

    @classmethod
    def settings_cls(cls) -> type[MillingSettings]:
        return MillingSettings

    @classmethod
    def state_cls(cls) -> type[MillingState]:
        return MillingState

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def beam_type(self) -> BeamType | None:
        return self._settings.beam_type

    @property
    def props_to_collect(self) -> PropertyNames:
        return self._settings.properties_to_collect

    @property
    def microscope(self) -> Microscope:
        return self._microscope

    @property
    def settings(self) -> MillingSettings:
        return self._settings

    @property
    def ctx(self) -> ActionContext:
        return self._ctx

    @property
    def state(self) -> MillingState:
        return MillingState(milling_slice=self._current_milling_slice)

    def set_state(self, state: MillingState) -> None:
        self._current_milling_slice = state.milling_slice

    @with_logging_context
    def execute(self) -> None:
        """
        Perform one milling step for the current slice if conditions are met.
        """
        if len(self._settings.milling_area) != 1:
            raise MillingError(
                f"Expected exactly one milling area, got {len(self._settings.milling_area)}."
            )

        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (self._ctx.slice - 1) % self._settings.execution_frequency != 0
        ):
            self._ctx.text_logger.info(
                f"Skipping '{self.name}' for slice {self._ctx.slice}."
            )
            # even if milling is skipped, we need to write properties for the next slice
            self.propagate_to_next()
            return

        self._ctx.text_logger.info(
            f"Started '{self.name}' for slice {self._ctx.slice}."
        )

        # set the properties of the microscope
        self.read_and_set_properties()

        # if not already set, set the area to mill in this slice
        if self._current_milling_slice is None:
            self._set_current_milling_slice()
            # hint for type checker
            assert self._current_milling_slice is not None

        self._ctx.text_logger.debug(
            f"Area to be milled in this slice in nanometers: {self._current_milling_slice}."
        )

        # perform the milling step
        self._ctx.text_logger.info("Starting the milling procedure.")
        self._microscope.beam.rectangle_milling(
            self._current_milling_slice,
            self._settings.milling_depth,
            self._settings.milling_direction,
            self._settings.pattern_type,
            self._settings.do_not_mill,
        )
        self._ctx.text_logger.info("Milling procedure completed.")

        # update the milling area for the next slice
        self._current_milling_slice = self._current_milling_slice.shifted_in_direction(
            self._settings.milling_direction, self._settings.slice_distance
        )

        self._check_milling_area_in_bounds(
            self._current_milling_slice, self._get_milling_area_nm()
        )

        self._ctx.text_logger.debug(
            f"Area to be milled in the next slice in nanometers: {self._current_milling_slice}."
        )

        props = self.collect_properties()
        self.write_properties(props, self._ctx.props_store.next)

        self._ctx.text_logger.info(
            f"Completed '{self.name}' for slice {self._ctx.slice}."
        )

    def test(self) -> None:
        raise MillingError(f"Testing is not implemented for {self.name}")

    def wait_for_background_threads(self) -> None:
        # no background threads to wait for
        pass

    def _get_milling_area_nm(self) -> NMArea:
        return self._settings.milling_area[0].to_nanometers(
            self._microscope.beam.resolution, self._microscope.beam.pixel_size
        )

    def _set_current_milling_slice(self) -> None:
        slice_dist = self._settings.slice_distance
        milling_area_nm = self._get_milling_area_nm()

        self._current_milling_slice = NMArea(
            origin=milling_area_nm.origin,
            width=milling_area_nm.width,
            height=slice_dist,
        )

        match self._settings.milling_direction:
            case Direction.DOWN:
                pass
            case Direction.UP:
                self._current_milling_slice.origin.y += (
                    milling_area_nm.height - slice_dist
                )
            case Direction.LEFT | Direction.RIGHT:
                raise MillingError(
                    f"Invalid milling direction {self._settings.milling_direction}"
                )

    @staticmethod
    def _check_milling_area_in_bounds(area: NMArea, bounds: NMArea) -> None:
        if not bounds.contains(area, tolerance=0.1):
            raise MillingError("Reached the boundaries of the designated milling area")
