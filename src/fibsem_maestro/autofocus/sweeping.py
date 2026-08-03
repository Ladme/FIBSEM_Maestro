# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from collections.abc import Iterator
from typing import Any

from fibsem_maestro.autofocus import SWEEPING_STRATEGIES
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.settings.sweeping_settings import SweepingSettings


class Sweeping:
    """
    Controller for parameter sweeping on a microscope beam.

    Manages sweeping a single configurable attribute of a beam over a range
    of values. A registered sweeping strategy generates candidate values for
    each repetition cycle, and only values within the beam's hardware limits
    are yielded. Out-of-range values are logged as warnings and skipped.

    Args:
        beam: The beam control whose attribute will be swept.
        settings: Sweeping configuration including the value
            range, number of steps, number of cycles, and strategy.
        sweep_attribute: Name of the microscope property that should be swept.
        txt_log: Logger for sweep-related status and warning messages.
    """

    def __init__(
        self,
        beam: BeamControl,
        settings: SweepingSettings,
        sweep_attribute: str,
        txt_log: TextLogger,
    ):
        self._beam = beam
        self._txt_log = txt_log

        self._settings = settings

        self._sweep_attribute = sweep_attribute

        self._sweeping_strategy = SWEEPING_STRATEGIES.get(self._settings.strategy.type)(
            self._settings.strategy
        )

    @property
    def sweep_attribute(self) -> str:
        """Name of the beam attribute being swept."""
        return self._sweep_attribute

    def sweep(self) -> Iterator[SweepStep]:
        """
        Iterate over all sweep steps across all configured cycles.

        Reads the current attribute value once before the sweep begins and
        uses it as the base for all generated values. Each yielded step
        carries its repetition index, value, and global step index.

        Yields:
            SweepStep: The next valid sweep step in sequence.
        """
        base = self.get_attribute_value()

        steps = (
            (rep, s)
            for rep in range(self._settings.cycles)
            for s in self._sweep_inner(rep, base)
        )

        for index, (repetition, value) in enumerate(steps):
            self._txt_log.info(f"Sweep cycle {repetition + 1}/{self._settings.cycles}.")
            yield SweepStep(repetition, value, index)

    def get_attribute_value(self) -> Any:
        """
        Return the current value of the sweeping attribute.

        The value is retrieved dynamically from the selected beam using the
        configured attribute name.

        Returns:
            Current value of the beam attribute being swept.
        """
        return getattr(self._beam, self._sweep_attribute)

    def set_attribute_value(self, value: Any) -> None:
        """
        Set the sweep target attribute on the beam to the given value.

        Args:
            value: The value to assign to the beam attribute.
        """
        setattr(self._beam, self._sweep_attribute, value)

    def evaluate_best_sweep(self, results: list[AutofocusResult]) -> float:
        """
        Determine the best sweep value from a list of autofocus results.

        Delegates to the configured sweeping strategy's evaluation method.

        Args:
            results: Autofocus results collected during the sweep, one per submitted job.

        Returns:
            The beam attribute value corresponding to the best autofocus result,
            as determined by the sweeping strategy.
        """
        return self._sweeping_strategy.evaluate(results)

    def _sweep_inner(self, repetition: int, base: float) -> Iterator[Any]:
        """
        Generate valid sweep values for a single repetition cycle.

        Produces candidate values via the sweeping strategy and filters out
        any that fall outside the beam's hardware limits. Out-of-range values
        are logged as warnings and skipped.

        Args:
            repetition: Index of the current sweep cycle, passed to the
                sweeping strategy to allow direction-alternating strategies
                such as zigzag.
            base: The attribute value at the start of the sweep, used as the
                centre point around which candidate values are generated.

        Yields:
            Valid sweep values that lie within the beam's hardware limits.
        """
        sweep_space = self._sweeping_strategy.generate(
            base,
            self._settings.range,
            self._settings.steps,
            repetition,
        )
        limits = self._beam.limits(self._sweep_attribute)

        for s in sweep_space:
            if limits[0] <= s <= limits[1]:
                yield float(s)
            else:
                self._txt_log.warning(
                    f"Sweeping value '{float(s)}' of an attribute '{self._sweep_attribute}' is out of range [{limits[0]} - {limits[1]}]."
                )
                # do not yield anything
                continue
