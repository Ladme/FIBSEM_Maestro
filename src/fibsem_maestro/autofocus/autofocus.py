# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from fibsem_maestro.autofocus.autofocus_registry import AutofocusRegistry

if TYPE_CHECKING:
    from collections.abc import Generator

    from fibsem_maestro.autofocus.autofunction_context import AutofunctionContext
    from fibsem_maestro.autofocus.jobs_manager import JobsManager


class AutofocusMode(ABC):
    @abstractmethod
    def execute(
        self, ctx: AutofunctionContext, jobs: JobsManager
    ) -> Generator[None, None, None]:
        pass


@AutofocusRegistry.register("basic")
class BasicMode(AutofocusMode):
    def execute(
        self, ctx: AutofunctionContext, jobs: JobsManager
    ) -> Generator[None, None, None]:
        with ctx.temporary_stage_x_offset():
            for sweep in ctx.sweeping.sweep():
                ctx.txt_log.info(
                    f"Autofunction step {sweep.index + 1} (repetition {sweep.repetition}): value {sweep.value}"
                )
                ctx.sweeping.set_attribute_value(sweep.value)
                image = ctx.microscope.beam.grab_frame()
                jobs.submit(ctx.make_resolution_job(image, sweep))

        yield from ()


"""
@AutofocusRegistry.register("line")
class LineMode(AutofocusMode):
    def __init__(self, autofunction: Autofunction, settings: LineModeSettings):
        self._af = autofunction
        self._settings = settings

    def execute(self) -> AutofocusStatus:
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

        return AutofocusStatus.DONE

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

        # iterate over repetitions
        for repetition, steps in groupby(
            af.sweeping.sweep(), key=lambda x: x.repetition
        ):
            af.txt_log.info(f"Line sweep cycle {repetition}")

            if repetition == 0:
                # start the image acquisition
                af.microscope.beam.start_acquisition()

            # blank to create a dark separator band between the stripes
            with af.microscope.total_blank():
                # at the start of the first repetition, wait for additional time
                if repetition == 0 and pre_delay > 0:
                    time.sleep(pre_delay)

                time.sleep(hold)

            # acquire part of the stripe with each sweep value
            for sweep in steps:
                af.sweeping.set_attribute_value(sweep.value)
                time.sleep(hold)

        # final hold [TODO: do we need it?]
        time.sleep(hold)
        af.microscope.beam.stop_acquisition()

    def _process_image(self, image: Image) -> None:
        forbidden_stripes = self._settings.forbidden_stripe_indices
        separator_threshold = self._settings.stripe_separator_threshold
        min_stripe_width = self._settings.minimal_stripe_width

        # convert the image to 8-bit
        img_8bit = image.to_8bit()

        # identify stripes from the image
        # each stripe corresponds to one sweeping repetition
        stripes = get_stripes(img_8bit, separator_threshold, min_stripe_width)

        # collect sweeps and group them
        sweep_groups = groupby(
            self._af.sweeping.sweep(), key=lambda step: step.repetition
        )

        for stripe, (rep, steps_iter) in zip(stripes, sweep_groups):
            # skip forbidden stripes
            if rep in forbidden_stripes:
                continue

            steps = list(steps_iter)

            # sanity check: stripe must have exactly the same length as the number of sweep steps for this repetition
            if len(stripe) != len(steps):
                raise ValueError(
                    f"Stripe length ({len(stripe)}) does not match sweep count ({len(steps)}) "
                    f"for repetition {rep}"
                )

            # submit a resolution calculation job for each line of the stripe
            for line_index, step in zip(stripe, steps):
                image_line = image[:, line_index]
                self._af.submit_resolution_job(image_line, step)


@AutofocusRegistry.register("step")
class StepMode(AutofocusMode):
    def __init__(self, autofunction: Autofunction, settings: StepModeSettings):
        self._af = autofunction
        _ = settings

        self._steps: Iterator[SweepStep] | None = None
        self._initialized = False

    def execute(self) -> AutofocusStatus:
        if not self._initialized:
            self._initialize()

        assert self._steps is not None
        af = self._af

        # if sweeping is exhausted, finalize and finish
        try:
            step = next(self._steps)
        except StopIteration:
            self._finalize()
            return AutofocusStatus.DONE

        af.txt_log.info(
            f"Autofunction step {step.index + 1} (repetition {step.repetition}): value {step.value}"
        )

        af.sweeping.set_attribute_value(step.value)
        image = af.microscope.beam.grab_frame()
        af.submit_resolution_job(image, step)

        return AutofocusStatus.IN_PROGRESS

    def _initialize(self) -> None:
        af = self._af
        af.clear_results()
        af.setup_microscope()

        self._steps = iter(af.sweeping.sweep())

        # keep stage offset applied across ticks.
        self._stage_ctx = af.temporary_stage_x_offset()
        self._stage_ctx.__enter__()

        self._initialized = True

    def _finalize(self) -> None:
        af = self._af

        af.wait_for_resolution_jobs()
        best = af.evaluate_best_sweep()
        af.txt_log.info(f"Best sweep value: {best}")
        af.sweeping.set_attribute_value(best)

        # restore stage position.
        if self._stage_ctx is not None:
            self._stage_ctx.__exit__(None, None, None)
            self._stage_ctx = None

        self._steps = None
        self._initialized = False


@AutofocusRegistry.register("manufacturer")
class ManufacturerMode(AutofocusMode):
    def __init__(self, autofunction: Autofunction, settings: ManufacturerModeSettings):
        self._af = autofunction
        _ = settings

    def execute(self) -> AutofocusStatus:
        raise NotImplementedError("Not yet implemented.")
"""
