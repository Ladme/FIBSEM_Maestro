# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from typing import TYPE_CHECKING

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.drift import Drift
from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.drift_correction import DRIFT_CALCULATION_MODES
from fibsem_maestro.drift_correction.error import DriftCorrectionError
from fibsem_maestro.logging.logging import with_logging_context
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.drift_correction_settings import DriftCorrectionSettings
from fibsem_maestro.settings.property_names import PropertyNames
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

        # set up the drift calculation method
        self._rebuild()

        self._is_initialized = False

        # rebuild whenever the settings change
        self._settings.on_change(lambda _: self._rebuild())

    def _rebuild(self) -> None:
        # TODO: we should probably only re-initialize if the template matching areas change
        self._is_initialized = False

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
    def settings(self) -> DriftCorrectionSettings:
        return self._settings

    @property
    def external_props(self) -> GlobalProperties:
        return self._settings.external_props

    @property
    def ctx(self) -> ActionContext:
        return self._ctx

    @property
    def state(self) -> DriftCorrectionState:
        return DriftCorrectionState(is_initialized=self._is_initialized)

    def set_state(self, state: DriftCorrectionState) -> None:
        self._is_initialized = state.is_initialized

    def propagate_to_next(self) -> None:
        super().propagate_to_next()
        self._drift_calc.if_skipped(self._ctx.slice)

    @with_logging_context
    def execute(self) -> None:
        """
        Acquire a frame, measure drift, and apply a compensating beam shift.

        Reads and applies stored microscope properties, runs the pre-drift
        hook, acquires a frame, and calculates the beam shift required to
        compensate for the measured drift. If the beam shift exceeds hardware
        limits and the stage is moved instead, a second frame is acquired and
        a fine-tuning correction is applied. After correction, the post-drift
        hook is called and the updated microscope properties are written to
        the next slice's store.

        Raises:
            DriftCorrectionError: If drift calculation fails and
                `settings.stop_at_failure` is `True`.
        """
        if not self._is_initialized:
            # initialize the drift calculation, if needed
            self._drift_calc.setup()
            self._is_initialized = True

        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (self._ctx.slice - 1) % self._settings.execution_frequency != 0
        ):
            self._ctx.text_logger.info(
                f"Skipping '{self.name}' for slice {self._ctx.slice}."
            )
            self.propagate_to_next()
            return

        self._ctx.text_logger.info(
            f"Started '{self.name}' for slice {self._ctx.slice}."
        )

        # set properties of the microscope
        self.read_and_set_properties()

        # prepare drift calculation
        self._drift_calc.before_calculate_drift(self._ctx.slice)

        # calculate drift and get beam shift to compensate for it
        beam_shift = self._calculate_correcting_beam_shift()

        # try to apply the beam shift
        if not (self._microscope.add_beam_shift_with_verification(beam_shift)):
            # this branch is taken if stage is moved
            self._ctx.text_logger.info(
                "Fine-tuning drift correction to remove stage positioning error."
            )
            beam_shift = self._calculate_correcting_beam_shift()

            # we assume that beam shift will always be in limit here
            # since the beam shift was reset in `add_beam_shift_with_verification`,
            # this is a reasonable assumption
            self._microscope.add_beam_shift_with_verification(beam_shift)

        # finalize drift calculation
        self._drift_calc.after_calculate_drift(self._ctx.slice)

        # collect and save the microscope properties for the next slice
        self.collect_and_write_properties(self._ctx.props_store.next)

        self._ctx.text_logger.info(
            f"Completed '{self.name}' for slice {self._ctx.slice}."
        )

    def test(self) -> None:
        raise DriftCorrectionError(f"Testing is not implemented for {self.name}")

    def wait_for_background_threads(self) -> None:
        # no background threads to wait for
        pass

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

    def _drift_to_beam_shift(self, drift: Drift):
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
