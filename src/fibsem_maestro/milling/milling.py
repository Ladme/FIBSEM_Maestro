# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import copy

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.outcome import Produced, StepOutcome
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.area import NMArea, RelativeArea
from fibsem_maestro.core.direction import Direction
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.milling.error import MillingError
from fibsem_maestro.settings.milling_settings import MillingSettings
from fibsem_maestro.workflow.actions import Actions


class MillingState(ActionState):
    milling_slice: NMArea | None = None
    used_up_area: RelativeArea | None = None
    """The designated milling area whose end was reached, or None."""


_AREA_USED_UP = "the milling area is used up; change it to continue"


@ACTION_REGISTRY.register("milling")
class Milling(Action[MillingSettings, MillingState]):
    """
    Performs focused ion beam milling one slice at a time.
    """

    _STATE_FIELDS = frozenset(
        {"milling_area", "slice_distance", "milling_direction", "beam_type"}
    )

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
        self._used_up_area: RelativeArea | None = None

    @classmethod
    def settings_cls(cls) -> type[MillingSettings]:
        return MillingSettings

    @classmethod
    def state_cls(cls) -> type[MillingState]:
        return MillingState

    @property
    def state(self) -> MillingState:
        return MillingState(
            milling_slice=self._current_milling_slice,
            used_up_area=self._used_up_area,
        )

    def set_state(self, state: MillingState) -> None:
        self._current_milling_slice = state.milling_slice
        self._used_up_area = state.used_up_area

    def reset_state(self) -> None:
        """
        Discard the milling position, but remember a used-up milling area.

        Changing the slice distance, direction or beam therefore restarts milling
        at the leading edge without lifting the end of the acquisition; only a
        different milling area does.
        """
        self.set_state(MillingState(used_up_area=self._used_up_area))
        self._ctx.state_store.write("state.yaml", self.state)

    def reset(self) -> None:
        """Reset the action to slice 0 and its default state, forgetting a used-up area."""
        self._used_up_area = None
        super().reset()

    def completion_reason(self) -> str | None:
        """
        Report the end of the acquisition once the milling area is used up.

        Returns:
            The reason while the used-up area is still the designated milling
            area, otherwise None.
        """
        if self._is_area_used_up():
            return _AREA_USED_UP
        return None

    def test(self) -> None:
        raise MillingError(f"Testing is not implemented for {self.name}")

    def _run_step(self) -> StepOutcome:
        if len(self._settings.milling_area) != 1:
            raise MillingError(
                f"Expected exactly one milling area, got {len(self._settings.milling_area)}."
            )

        if self._is_area_used_up():
            raise MillingError("The milling area is used up; change it to continue.")

        milling_area_nm = self._get_milling_area_nm()
        if self._current_milling_slice is None:
            self._set_current_milling_slice()
        assert self._current_milling_slice is not None

        # never mill outside the designated area, whatever state was stored
        self._check_milling_area_in_bounds(self._current_milling_slice, milling_area_nm)

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

        if not self._current_milling_slice.has_size():
            raise MillingError(
                f"Area to be milled has no size: {self._current_milling_slice}"
            )

        if milling_area_nm.contains(self._current_milling_slice, tolerance=0.1):
            self._ctx.text_logger.debug(
                f"Area to be milled in the next slice in nanometers: {self._current_milling_slice}."
            )
        else:
            # the next slice would leave the area: this slice was the last one; the
            # workflow finishes before the next slice (see `completion_reason`)
            self._used_up_area = self._settings.milling_area[0]
            self._ctx.text_logger.info("The milling area is used up.")

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

    def _is_area_used_up(self) -> bool:
        areas = self._settings.milling_area
        return (
            self._used_up_area is not None
            and len(areas) == 1
            and self._used_up_area == areas[0]
        )

    @staticmethod
    def _check_milling_area_in_bounds(area: NMArea, bounds: NMArea) -> None:
        if not bounds.contains(area, tolerance=0.1):
            raise MillingError(
                f"The slice to be milled ({area}) lies outside the designated milling area."
            )
