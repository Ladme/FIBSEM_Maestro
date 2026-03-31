# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.autofunction_settings import AutofunctionSettings


class AutofunctionContext:
    def __init__(
        self,
        microscope: Microscope,
        sweeping: Sweeping,
        criterion: Criterion,
        settings: AutofunctionSettings,
        txt_log: TextLogger,
    ):
        self.microscope = microscope
        self.sweeping = sweeping
        self.txt_log = txt_log
        self.settings = settings

        self._criterion = criterion

    @contextmanager
    def temporary_stage_x_offset(self) -> Iterator[None]:
        """
        Temporarily move the stage in X to a nearby focusing area and
        always restore the original position afterward.
        """
        # move the stage away
        self.microscope._control.try_move_stage_position(
            StagePosition(x=-self.settings.delta_x)
        )
        self.txt_log.info(
            f"Moving stage to focusing area (X offset {-self.settings.delta_x:+g})"
        )

        try:
            yield
        finally:
            # move the stage back
            self.microscope._control.try_move_stage_position(
                StagePosition(x=self.settings.delta_x)
            )
            self.txt_log.info(
                f"Restoring stage position (X offset {self.settings.delta_x:+g})"
            )

    def make_resolution_job(
        self, image: Image, sweep: SweepStep
    ) -> Callable[[], AutofocusResult]:
        def fn() -> AutofocusResult:
            try:
                value = self._criterion.calculate_sharpness(image)
                self.txt_log.info(f"Sharpness calculation for sweep {sweep}: {value}")
                return AutofocusResult(value, sweep)
            except Exception as exc:
                self.txt_log.warning(
                    f"Sharpness calculation for sweep {sweep.value} failed: {exc}."
                )
                raise

        return fn
