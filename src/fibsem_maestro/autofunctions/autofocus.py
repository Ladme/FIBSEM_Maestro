# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from itertools import groupby
from typing import TYPE_CHECKING

from fibsem_maestro.autofunctions.autofocus_registry import AutofocusRegistry
from fibsem_maestro.autofunctions.error import AutofunctionError

if TYPE_CHECKING:
    from fibsem_maestro.autofunctions.autofunction import Autofunction
    from fibsem_maestro.settings.autofunction_settings import (
        AutofocusMode as AutofocusModeSettings,
    )
    from fibsem_maestro.settings.autofunction_settings import (
        BasicMode as BasicModeSettings,
    )
    from fibsem_maestro.settings.autofunction_settings import (
        LineMode as LineModeSettings,
    )
    from fibsem_maestro.settings.autofunction_settings import (
        ManufacturerMode as ManufacturerModeSettings,
    )
    from fibsem_maestro.settings.autofunction_settings import (
        StepMode as StepModeSettings,
    )


class AutofocusMode(ABC):
    @abstractmethod
    def __init__(self, autofunction: Autofunction, settings: AutofocusModeSettings):
        pass

    @abstractmethod
    def execute(self) -> None:
        pass


@AutofocusRegistry.register("basic")
class BasicMode(AutofocusMode):
    def __init__(self, autofunction: Autofunction, settings: BasicModeSettings):
        _ = settings
        self._af = autofunction

    def execute(self) -> None:
        af = self._af
        af.clear_results()

        af.setup_microscope()
        with af.temporary_stage_x_offset():
            for i, (repetition, sweep) in enumerate(af.sweeping.sweep()):
                af.txt_log.info(
                    f"Autofunction step {i + 1} (repetition {repetition}): value {sweep}"
                )
                af.sweeping.set_attribute_value(sweep)
                image = af.microscope.beam.grab_frame()
                af.submit_resolution_job(image, sweep)

        af.wait_for_resolution_jobs()
        best = af.evaluate_best_sweep()
        af.txt_log.info(f"Best sweep value: {best}")
        af.sweeping.set_attribute_value(best)


@AutofocusRegistry.register("line")
class LineMode(AutofocusMode):
    def __init__(self, autofunction: Autofunction, settings: LineModeSettings):
        self._af = autofunction
        self._settings = settings

    def execute(self) -> None:
        af = self._af
        af.clear_results()

        with af.temporary_stage_x_offset():
            af.microscope.blank_screen()  # TODO: is this necessary?
            af.setup_microscope()

            line_time = self._estimate_line_time()

            self._variable_sweeping_during_scan(line_time)

            # grab final image after acquisition
            self.line_focus_image = af.microscope.beam.get_image(
                crop_to_scanning_area=True
            )

            # schedule resolution jobs from the image
            self._process_image(self.line_focus_image)

        af.wait_for_resolution_jobs()
        best = af.evaluate_best_sweep()
        af.txt_log.info(f"Best sweep value: {best}")
        af.sweeping.set_attribute_value(best)

    def _estimate_line_time(self) -> float:
        af = self._af
        imaging = af.imaging_settings

        dwell = imaging.dwell_time
        if dwell is None:
            raise AutofunctionError(
                "Imaging setting 'dwell_time' must be set for line autofocus."
            )

        line_integration = imaging.line_integration
        if line_integration is None:
            raise AutofunctionError(
                "Imaging setting 'line_integration' must be set for line autofocus."
            )

        resolution = imaging.resolution
        if resolution is None:
            raise AutofunctionError(
                "Imaging setting 'resolution' must be set for line autofocus."
            )

        estimated = dwell * line_integration * resolution[0]

        area = imaging.scanning_area
        if area and area.width > 0 and area.height > 0:
            estimated *= area.width

        return estimated

    def _variable_sweeping_during_scan(self, line_time: float) -> None:
        af = self._af

        pre_delay = self._settings.pre_imaging_delay
        hold = self._settings.lines_per_sweep * line_time

        for repetition, steps in groupby(af.sweeping.sweep(), key=lambda x: x[0]):
            af.txt_log.info(f"Line sweep cycle {repetition}")

            if repetition == 0:
                af.microscope.beam.start_acquisition()

            with af.microscope.total_blank():
                # at the start of the first repetition, wait for additional time
                if repetition == 0 and pre_delay > 0:
                    time.sleep(pre_delay)

                time.sleep(hold)

            for _, sweep in steps:
                af.sweeping.set_attribute_value(sweep)
                time.sleep(hold)

        # final hold [TODO: do we need it?]
        time.sleep(hold)
        af.microscope.beam.stop_acquisition()


@AutofocusRegistry.register("step")
class StepMode(AutofocusMode):
    def __init__(self, autofunction: Autofunction, settings: StepModeSettings):
        self._af = autofunction
        _ = settings

    def execute(self) -> None:
        raise NotImplementedError("Not yet implemented.")


@AutofocusRegistry.register("manufacturer")
class ManufacturerMode(AutofocusMode):
    def __init__(self, autofunction: Autofunction, settings: ManufacturerModeSettings):
        self._af = autofunction
        _ = settings

    def execute(self) -> None:
        raise NotImplementedError("Not yet implemented.")
