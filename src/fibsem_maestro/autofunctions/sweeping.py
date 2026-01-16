# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Iterator
from typing import Any

from fibsem_maestro.autofunctions.result import AutofocusResult
from fibsem_maestro.autofunctions.sweep_step import SweepStep
from fibsem_maestro.autofunctions.sweeping_registry import SweepingRegistry
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.microscope_control import (
    MicroscopeControl,
)
from fibsem_maestro.settings.sweeping_settings import SweepingSettings


class Sweeping:
    """
    Controller for parameter sweeping on a microscope beam.

    This class manages sweeping a single configurable attribute of a selected
    microscope beam over a range of values. It uses a registered sweeping strategy
    to generate candidate values and yields only values that are within the hardware
    limits of the beam.

    The sweeping behavior is fully defined by a `SweepingSettings` object and
    updates dynamically when settings change.
    """

    def __init__(
        self,
        microscope_control: MicroscopeControl,
        settings: SweepingSettings,
        txt_log: TextLogger,
    ):
        """
        Initialize a sweeping controller.

        Args:
            microscope_control (MicroscopeControl):
                Microscope control interface providing access to beam objects.
            settings (SweepingSettings):
                Initial sweeping configuration.
            txt_log (TextLogger):
                Logger for sweep-related messages.
        """
        self._microscope_control = microscope_control
        self._txt_log = txt_log

        self._apply_settings(settings)
        self._settings.on_change(self._update)

        self._base: float | None = None
        self.set_base()

    def _update(self, settings: SweepingSettings) -> None:
        """
        Update sweeping configuration when settings change.

        This method is registered as a callback and re-applies all sweeping
        parameters whenever the settings object is updated.

        Args:
            settings (SweepingSettings):
                Updated sweeping settings.
        """
        self._apply_settings(settings)

    def _apply_settings(self, settings: SweepingSettings) -> None:
        """
        Apply all configurable fields from the given settings object.

        Args:
            settings (SweepingSettings):
                Sweeping configuration to apply.
        """
        self._settings = settings

        match settings.target_beam:
            case BeamType.ELECTRON:
                self._beam = self._microscope_control.electron_beam
            case BeamType.ION:
                self._beam = self._microscope_control.ion_beam

        self._sweep_attribute = settings.target_attribute

        self._sweeping_strategy = SweepingRegistry.get(self._settings.strategy.type)(
            self._settings.strategy
        )

    def sweep(self) -> Iterator[SweepStep]:
        steps = (
            (rep, s)
            for rep in range(self._settings.cycles)
            for s in self._sweep_inner(rep)
        )

        for index, (repetition, value) in enumerate(steps):
            self._txt_log.info(f"Sweep cycle {repetition}/{self._settings.cycles}.")
            yield SweepStep(repetition, value, index)

    def get_attribute_value(self) -> Any:
        """
        Return the current value of the sweeping attribute.

        The value is retrieved dynamically from the selected beam using the
        configured attribute name.

        Returns:
            Any:
                Current value of the beam attribute being swept.
        """
        return getattr(self._beam, self._sweep_attribute)

    def set_attribute_value(self, value: Any) -> None:
        """
        Set the sweeping attribute of the beam to the specified value.
        """
        setattr(self._beam, self._sweep_attribute, value)

    def evaluate_best_sweep(self, results: list[AutofocusResult]) -> float:
        """
        Evaluate the best sweep value based on the sweeping strategy and return it.
        """
        return self._sweeping_strategy.evaluate(results)

    def set_base(self) -> None:
        """
        Set the base value of the sweeping attribute based on the current value of the beam.
        """
        self._base = self.get_attribute_value()

    def _sweep_inner(self, repetition: int) -> Iterator[float]:
        """
        Generate valid sweep values for a single repetition.

        This method generates candidate values using the configured sweeping
        strategy and filters out values that fall outside the hardware limits
        of the target beam.

        Args:
            repetition (int):
                Index of the current sweep repetition, passed to the sweeping strategy.

        Yields:
            float:
                Valid sweep values within the beam's allowed limits.
        """
        assert self._base is not None

        sweep_space = self._sweeping_strategy.generate(
            self._base, self._settings.range, self._settings.steps, repetition
        )
        limits = self._beam.limits(self._sweep_attribute)

        for s in sweep_space:
            if limits[0] <= s <= limits[1]:
                yield s
            else:
                self._txt_log.warning(
                    f"Sweeping value '{s}' of an attribute '{self._sweep_attribute}' is out of range [{limits[0]} - {limits[1]}]."
                )
                # do not yield anything
                continue
