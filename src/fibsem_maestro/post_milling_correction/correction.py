# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import numpy as np

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.outcome import Produced, StepOutcome
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.direction import Direction
from fibsem_maestro.milling.milling import Milling
from fibsem_maestro.post_milling_correction.error import PostMillingCorrectionError
from fibsem_maestro.settings.post_milling_correction_settings import (
    DynamicFocusMode,
    ManualMode,
    PostMillingCorrectionSettings,
)

_ION_ELECTRON_ANGLE_RAD = float(np.deg2rad(52.0))
"""Angle between the ion and electron beams."""


class PostMillingCorrectionState(ActionState):
    pass


@ACTION_REGISTRY.register("post_milling_correction")
class PostMillingCorrection(
    Action[
        PostMillingCorrectionSettings,
        PostMillingCorrectionState,
    ]
):
    """
    Compensates for the cross-section face receding after each milling step.
    """

    @classmethod
    def settings_cls(cls) -> type[PostMillingCorrectionSettings]:
        """
        Class of the class used for the action's settings.
        """
        return PostMillingCorrectionSettings

    @classmethod
    def state_cls(cls) -> type[PostMillingCorrectionState]:
        return PostMillingCorrectionState

    @property
    def state(self) -> PostMillingCorrectionState:
        # post milling correction has no persistent internal state
        return PostMillingCorrectionState()

    def set_state(
        self,
        state: PostMillingCorrectionState,
    ) -> None:
        _ = state

    def test(self) -> None:
        raise PostMillingCorrectionError(f"Testing is not implemented for {self.name}")

    def _run_step(self) -> StepOutcome:
        match self._settings.correction_mode:
            case ManualMode() as mode:
                self._apply_correction(mode.y_correction, mode.wd_correction)
            case DynamicFocusMode():
                self._apply_correction(*self._geometric_correction())
        return Produced(self.collect_properties())

    def _resolve_milling(self) -> Milling:
        milling = self._actions.named(self._settings.linked_milling)
        if not isinstance(milling, Milling):
            raise PostMillingCorrectionError(
                f"Linked action is not a Milling action: {milling.name}"
            )
        return milling

    def _perform_manual_correction(self, mode: ManualMode) -> None:
        self._ctx.text_logger.info(
            f"Performing manual post milling correction: y_correction={mode.y_correction}, wd_correction={mode.wd_correction}."
        )

        self._microscope.add_beam_shift_with_verification(
            delta=BeamShift(0, mode.y_correction)
        )
        self._microscope.beam.working_distance += mode.wd_correction

    def _geometric_correction(self) -> tuple[float, float]:
        """
        Compute the correction from the linked milling's slice distance.

        Returns:
            The y correction and working-distance correction, both in nm.
        """
        milling = self._resolve_milling().settings
        y_correction = float(np.cos(_ION_ELECTRON_ANGLE_RAD) * milling.slice_distance)
        wd_correction = float(np.sin(_ION_ELECTRON_ANGLE_RAD) * milling.slice_distance)

        # milling up moves the face the other way
        if milling.milling_direction is Direction.UP:
            y_correction, wd_correction = -y_correction, -wd_correction

        return y_correction, wd_correction

    def _apply_correction(self, y_correction: float, wd_correction: float) -> None:
        """
        Apply a vertical image shift and a working-distance change.

        Args:
            y_correction: Vertical shift in image coordinates, in nm.
            wd_correction: Working-distance change, in nm.
        """
        self._ctx.text_logger.info(
            f"Performing post milling correction: y_correction={y_correction} nm, "
            f"wd_correction={wd_correction} nm."
        )
        image_to_beam_shift = self._microscope.beam.image_to_beam_shift
        self._microscope.add_beam_shift_with_verification(
            delta=BeamShift(0.0, image_to_beam_shift[1] * y_correction)
        )
        self._microscope.beam.working_distance += wd_correction
