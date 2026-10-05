# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import copy

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.outcome import Produced, StepOutcome
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.area import NMArea
from fibsem_maestro.core.direction import Direction
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.milling.error import MillingError
from fibsem_maestro.settings.milling_settings import MillingSettings
from fibsem_maestro.workflow.actions import Actions


class MillingState(ActionState):
    milling_slice: NMArea | None


@ACTION_REGISTRY.register("milling")
class Milling(Action[MillingSettings, MillingState]):
    """
    Performs focused ion beam milling one slice at a time.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: MillingSettings,
        ctx: ActionContext,
        actions: Actions,
    ):
        super().__init__(name, microscope, settings, ctx, actions)
        self._current_milling_slice: NMArea | None = None

    @classmethod
    def settings_cls(cls) -> type[MillingSettings]:
        return MillingSettings

    @classmethod
    def state_cls(cls) -> type[MillingState]:
        return MillingState

    @property
    def state(self) -> MillingState:
        return MillingState(milling_slice=self._current_milling_slice)

    def set_state(self, state: MillingState) -> None:
        self._current_milling_slice = state.milling_slice

    def test(self) -> None:
        raise MillingError(f"Testing is not implemented for {self.name}")

    def _run_step(self) -> StepOutcome:
        if len(self._settings.milling_area) != 1:
            raise MillingError(
                f"Expected exactly one milling area, got {len(self._settings.milling_area)}."
            )

        if self._current_milling_slice is None:
            self._set_current_milling_slice()
        assert self._current_milling_slice is not None

        self._ctx.text_logger.debug(
            f"Area to be milled in this slice in nanometers: {self._current_milling_slice}."
        )
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

        return Produced(self.collect_properties())

    def _get_milling_area_nm(self) -> NMArea:
        return self._settings.milling_area[0].to_nanometers(
            self._microscope.beam.resolution, self._microscope.beam.pixel_size
        )

    def _set_current_milling_slice(self) -> None:
        slice_dist = self._settings.slice_distance
        milling_area_nm = self._get_milling_area_nm()

        origin = copy.copy(milling_area_nm.origin)

        match self._settings.milling_direction:
            case Direction.DOWN:
                pass
            case Direction.UP:
                origin.y += milling_area_nm.height - slice_dist
            case Direction.LEFT | Direction.RIGHT:
                raise MillingError(
                    f"Invalid milling direction {self._settings.milling_direction}"
                )

        self._current_milling_slice = NMArea(
            origin=origin,
            width=milling_area_nm.width,
            height=slice_dist,
        )

    @staticmethod
    def _check_milling_area_in_bounds(area: NMArea, bounds: NMArea) -> None:
        if not bounds.contains(area, tolerance=0.1):
            raise MillingError("Reached the boundaries of the designated milling area")
