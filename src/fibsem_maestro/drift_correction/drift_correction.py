# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import TYPE_CHECKING

from fibsem_maestro.action.action import Action, ActionConfig
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.drift import Drift
from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.drift_correction import DRIFT_CALCULATION_MODES
from fibsem_maestro.drift_correction.error import DriftCorrectionError
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.drift_correction_settings import DriftCorrectionSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.image.image_store import ImageStore
from fibsem_maestro.store.props.props_store import PropsStore

if TYPE_CHECKING:
    from fibsem_maestro.drift_correction.drift_calculation_mode import (
        DriftCalculationMode,
    )


@ACTION_REGISTRY.register("drift_correction")
class DriftCorrection(Action[DriftCorrectionSettings, None]):
    """
    Corrects sample drift between slices by applying a compensating beam shift.
    """

    def __init__(
        self,
        config: ActionConfig[DriftCorrectionSettings],
    ):
        self._name = config.name
        self._microscope = config.microscope
        self._settings = config.settings
        self._props_store = config.props_store
        self._image_store = config.image_store
        self._txt_log = config.txt_log
        self._img_log = config.img_log

        # set up the drift calculation method
        self._drift_calc_name = self._settings.drift_calculation_mode.type
        self._drift_calc: DriftCalculationMode = DRIFT_CALCULATION_MODES.get(
            self._drift_calc_name
        )(
            f"{self._name} {self._drift_calc_name}",
            self._microscope,
            self._settings.drift_calculation_mode,
            self._image_store,
            self._txt_log,
            self._img_log,
        )

    @classmethod
    def settings_cls(cls) -> type[DriftCorrectionSettings]:
        return DriftCorrectionSettings

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def props_file(self) -> str:
        return f"{str(self.name_with_underscores)}_props.yaml"

    @property
    def props_store(self) -> PropsStore:
        return self._props_store

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
    def txt_log(self) -> TextLogger:
        return self._txt_log

    @property
    def settings(self) -> DriftCorrectionSettings:
        return self._settings

    @property
    def external_props(self) -> GlobalProperties:
        return self._settings.external_props

    @property
    def image_store(self) -> ImageStore[Image8Bit]:
        return self._image_store

    def setup(self, store: ImageStore[Image8Bit] | None = None) -> None:
        """
        Initialize the drift calculation mode before acquisition begins.

        Delegates to the configured `DriftCalculationMode.setup`, which
        performs any one-time preparation required before the first slice -
        for example, acquiring reference templates.

        Args:
            store: Optional image store to use for template loading/saving.
                If not provided, the image store for the current slice is used.
        """
        self._drift_calc.setup(store)

    def execute(self, slice_number: int, links: None = None) -> None:
        """
        Acquire a frame, measure drift, and apply a compensating beam shift.

        Reads and applies stored microscope properties, runs the pre-drift
        hook, acquires a frame, and calculates the beam shift required to
        compensate for the measured drift. If the beam shift exceeds hardware
        limits and the stage is moved instead, a second frame is acquired and
        a fine-tuning correction is applied. After correction, the post-drift
        hook is called and the updated microscope properties are written to
        the next slice's store.

        Args:
            slice_number: The current slice index.

        Raises:
            DriftCorrectionError: If drift calculation fails and
                `settings.stop_at_failure` is `True`.
        """
        _ = links

        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (slice_number - 1) % self._settings.execution_frequency != 0
        ):
            self._txt_log.info(f"Skipping {self.name} for slice {slice_number}.")
            # even if drift correction is skipped, we need to write properties for the next slice
            self.write_properties(self.read_properties(), self._props_store.next)
            # and potentially perform some other operations
            self._drift_calc.if_skipped(slice_number)
            return

        # set properties of the microscope
        self.read_and_set_properties()

        # prepare drift calculation
        self._drift_calc.before_calculate_drift(slice_number)

        # calculate drift and get beam shift to compensate for it
        beam_shift = self._calculate_correcting_beam_shift()

        # try to apply the beam shift
        if not (self._microscope.add_beam_shift_with_verification(beam_shift)):
            # this branch is taken if stage is moved
            self._txt_log.info(
                "Fine-tuning drift correction to remove stage positioning error."
            )
            beam_shift = self._calculate_correcting_beam_shift()

            # we assume that beam shift will always be in limit here
            # since the beam shift was reset in `add_beam_shift_with_verification`,
            # this is a reasonable assumption
            self._microscope.add_beam_shift_with_verification(beam_shift)

        # finalize drift calculation
        self._drift_calc.after_calculate_drift(slice_number)

        # collect and save the microscope properties for the next slice
        self.collect_and_write_properties(self._props_store.next)

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

            self._txt_log.warning(
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
