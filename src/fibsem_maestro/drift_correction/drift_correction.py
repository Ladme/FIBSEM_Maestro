# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from typing import TYPE_CHECKING

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.outcome import Produced, StepOutcome
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.drift import Drift
from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.drift_correction import DRIFT_CALCULATION_MODES
from fibsem_maestro.drift_correction.error import DriftCorrectionError
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.drift_correction_settings import DriftCorrectionSettings
from fibsem_maestro.workflow.actions import Actions

if TYPE_CHECKING:
    from fibsem_maestro.drift_correction.drift_calculation_mode import (
        DriftCalculationMode,
    )


class DriftCorrectionState(ActionState):
    is_initialized: bool = False


@ACTION_REGISTRY.register("drift_correction")
class DriftCorrection(Action[DriftCorrectionSettings, DriftCorrectionState]):
    """
    Corrects sample drift between slices by applying a compensating beam shift.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: DriftCorrectionSettings,
        ctx: ActionContext,
        actions: Actions,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._ctx = ctx
        self._actions = actions

        self._is_initialized = False
        # set up the drift calculation method
        self._rebuild()
        # rebuild whenever the settings change
        self._settings.on_change(lambda _: self._rebuild())

    def _rebuild(self) -> None:
        # TODO: we should re-initialize if the template matching areas change
        # self._is_initialized = False

        self._drift_calc_name = self._settings.drift_calculation_mode.type
        self._drift_calc: DriftCalculationMode = DRIFT_CALCULATION_MODES.get(
            self._drift_calc_name
        )(
            self._microscope,
            self._settings.drift_calculation_mode,
            self._ctx.image_store(Image8Bit),
            self._ctx.text_logger.derive(self._drift_calc_name),
            self._ctx.image_logger,
        )

    @classmethod
    def settings_cls(cls) -> type[DriftCorrectionSettings]:
        return DriftCorrectionSettings

    @classmethod
    def state_cls(cls) -> type[DriftCorrectionState]:
        return DriftCorrectionState

    @property
    def state(self) -> DriftCorrectionState:
        return DriftCorrectionState(is_initialized=self._is_initialized)

    def set_state(self, state: DriftCorrectionState) -> None:
        self._is_initialized = state.is_initialized

    def carry_over_to_next(self) -> None:
        super().carry_over_to_next()
        self._drift_calc.if_skipped(self._ctx.slice)

    def _run_step(self) -> StepOutcome:
        if not self._is_initialized:
            self._ctx.text_logger.debug(f"Initializing drift correction '{self.name}'.")
            self._drift_calc.setup()
            self._is_initialized = True
            # TODO: should we do this?
            self.read_and_set_properties()

        if self._microscope.beam.scan_rotation != 0:
            raise DriftCorrectionError(
                "Scan rotation must be zero for drift correction."
            )

        self._drift_calc.before_calculate_drift(self._ctx.slice)

        beam_shift = self._calculate_correcting_beam_shift()
        if not self._microscope.add_beam_shift_with_verification(beam_shift):
            # the stage was moved instead; remove its positioning error
            self._ctx.text_logger.info(
                "Fine-tuning drift correction to remove stage positioning error."
            )
            # the beam shift was reset by the stage move, so this one is in range
            self._microscope.add_beam_shift_with_verification(
                self._calculate_correcting_beam_shift()
            )

        self._drift_calc.after_calculate_drift(self._ctx.slice)
        return Produced(self.collect_properties())

    def test(self) -> None:
        raise DriftCorrectionError(f"Testing is not implemented for {self.name}")

    def _calculate_correcting_beam_shift(self) -> BeamShift:
        """
        Calculate the beam shift required to compensate for the measured drift.

        Returns:
            The beam shift to apply in order to compensate for the detected
            drift, or a zero shift if drift calculation failed and the
            acquisition is configured to continue.

        Raises:
            DriftCorrectionError: If drift calculation fails and
                `settings.stop_at_failure` is `True`.
        """
        drift = self._drift_calc.calculate_drift()

        if not drift.is_valid():
            if self._settings.stop_at_failure:
                raise DriftCorrectionError(
                    "Drift correction failed: could not calculate drift."
                )

            self._ctx.text_logger.warning(
                "Drift correction failed: could not calculate drift. Not performing correction."
            )

        # convert drift to beam shift
        return self._drift_to_beam_shift(drift)

    def _drift_to_beam_shift(self, drift: Drift) -> BeamShift:
        """
        Convert a drift measurement in nanometers to a compensating beam shift.

        Args:
            drift: The measured drift in nanometers.

        Returns:
            The beam shift to apply in order to compensate for the drift.
        """
        return BeamShift(
            x=(drift.x or 0.0) * self._microscope.beam.image_to_beam_shift[0],
            y=(drift.y or 0.0) * self._microscope.beam.image_to_beam_shift[1],
        )
