# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from itertools import groupby
from typing import TYPE_CHECKING

from fibsem_maestro.autofocus.autofocus_registry import AutofocusRegistry
from fibsem_maestro.autofocus.error import AutofunctionError
from fibsem_maestro.core.image_tools import get_stripes
from fibsem_maestro.settings.autofunction_settings import LineMode as LineModeSettings

if TYPE_CHECKING:
    from collections.abc import Generator

    from fibsem_maestro.autofocus.autofunction_context import AutofunctionContext
    from fibsem_maestro.autofocus.jobs_manager import JobsManager
    from fibsem_maestro.autofocus.sweep_step import SweepStep
    from fibsem_maestro.core.image import Image


class AutofocusMode(ABC):
    """
    Abstract base class for autofocus mode implementations.

    Each subclass encodes a specific strategy for sweeping a beam parameter
    and submitting sharpness evaluation jobs. Concrete modes are registered
    with `AutofocusRegistry` and retrieved by name at runtime.
    """

    @abstractmethod
    def execute(
        self, ctx: AutofunctionContext, jobs: JobsManager
    ) -> Generator[None, None, None]:
        """
        Drive the autofocus sweep and submit sharpness evaluation jobs.

        Args:
            ctx: Shared execution environment providing access to the
                microscope, sweeping controller, criterion, and logger.
            jobs: Job manager to which sharpness evaluation callables are
                submitted for asynchronous execution.
        """
        pass


@AutofocusRegistry.register("basic")
class BasicMode(AutofocusMode):
    """
    Autofocus mode that acquires one image per swept attribute value.

    For each value in the sweep range, the target beam attribute is set,
    a full frame is acquired, and its sharpness is evaluated. Once all
    frames have been collected and their sharpness scores computed, the
    best attribute value can be determined from the results.

    The stage is temporarily displaced to a nearby focusing area for the
    duration of the sweep and restored to its original position afterward.
    """

    def execute(
        self, ctx: AutofunctionContext, jobs: JobsManager
    ) -> Generator[None, None, None]:
        with ctx.temporary_stage_x_offset():
            for sweep in ctx.sweeping.sweep():
                ctx.txt_log.info(
                    f"Autofunction step {sweep.index + 1} (repetition {sweep.repetition + 1}): value {sweep.value}"
                )
                ctx.sweeping.set_attribute_value(sweep.value)
                image = ctx.microscope.beam.grab_frame()
                jobs.submit(ctx.make_resolution_job(image, sweep))

        yield from ()


@AutofocusRegistry.register("line")
class LineMode(AutofocusMode):
    def execute(
        self, ctx: AutofunctionContext, jobs: JobsManager
    ) -> Generator[None, None, None]:
        with ctx.temporary_stage_x_offset():
            line_time = self._estimate_line_time(ctx)

            # generate sweep steps once so both acquisition and processing see the same steps
            sweep_steps = list(ctx.sweeping.sweep())

            self._variable_sweeping_during_scan(ctx, line_time, sweep_steps)

            line_focus_image = ctx.microscope.beam.get_image(crop_to_scanning_area=True)
            self._process_image(ctx, jobs, line_focus_image, sweep_steps)

        yield from ()

    def _estimate_line_time(self, ctx: AutofunctionContext) -> float:
        """
        Estimate the time required to scan a single line.

        Args:
            ctx: Shared execution environment providing access to the microscope
                and beam parameters.

        Returns:
            Estimated line scan time in seconds.
        """
        dwell_time = ctx.microscope.beam.dwell_time
        line_integration = ctx.microscope.beam.line_integration
        resolution = ctx.microscope.beam.resolution
        scanning_area = ctx.microscope.beam.scanning_area

        return dwell_time * line_integration * resolution.width * scanning_area.width

    def _variable_sweeping_during_scan(
        self,
        ctx: AutofunctionContext,
        line_time: float,
        sweep_steps: list[SweepStep],
    ) -> None:
        """
        Sweep the target beam attribute while an image is being acquired line by line.

        Starts a continuous acquisition and iterates over sweep cycles (repetitions).
        Before each cycle, the beam is blanked for `lines_per_sweep` lines to create
        a dark separator band. The beam is then unblanked and the target attribute is
        set to each sweep step value in turn, holding for `lines_per_sweep` lines at
        each value.

        The resulting image has the following structure:

        .. code-block:: text

            [dark separator]
            [lines at step 0]   <- first repetition
            [lines at step 1]
            ...
            [lines at step N]
            [dark separator]
            [lines at step 0]   <- second repetition
            ...

        Each group of lines between two dark separators forms one stripe, corresponding
        to one sweep cycle. Within a stripe, each contiguous block of `lines_per_sweep`
        rows corresponds to one sweep step value, and is later matched to its sweep step
        by index in `_process_image`.

        At the start of the first cycle, an optional `pre_imaging_delay` is applied
        while the beam is blanked, to allow the system to stabilise before scanning begins.

        Args:
            ctx: Shared execution environment providing access to the microscope,
                sweeping controller, and logger.
            line_time: Estimated time to scan a single line in seconds, used to
                compute the hold duration per sweep step.
            sweep_steps: Pre-generated list of sweep steps, shared with
                `_process_image` to ensure consistency.
        """
        mode = ctx.settings.mode
        assert isinstance(mode, LineModeSettings)

        pre_delay = mode.pre_imaging_delay
        hold = mode.lines_per_sweep * line_time

        ctx.microscope.beam.start_acquisition()
        try:
            # group consecutive sweep steps by repetition index so that each
            # cycle produces one stripe in the acquired image
            for repetition, steps in groupby(sweep_steps, key=lambda x: x.repetition):
                ctx.txt_log.info(f"Line sweep cycle {repetition}")

                # blank to create a dark separator band between the stripes
                with ctx.microscope.beam.total_blanked():
                    if repetition == 0 and pre_delay > 0:
                        time.sleep(pre_delay)
                    time.sleep(hold)

                # acquire part of the stripe with each sweep value
                for sweep in steps:
                    ctx.sweeping.set_attribute_value(sweep.value)
                    time.sleep(hold)
        finally:
            ctx.microscope.beam.stop_acquisition()

    def _process_image(
        self,
        ctx: AutofunctionContext,
        jobs: JobsManager,
        image: Image,
        sweep_steps: list[SweepStep],
    ) -> None:
        """
        Extract per-line sharpness jobs from the acquired image.

        Identifies horizontal stripes in the image using dark separator rows
        produced by blanking during acquisition. Each stripe corresponds to one
        sweep cycle (repetition). Within each stripe, individual rows are matched
        to their corresponding sweep steps by index, and a sharpness evaluation
        job is submitted for each row.

        Stripes listed in `forbidden_stripe_indices` are skipped entirely.

        An `AutofocusError` is raised if the number of rows in a stripe does not
        match the number of sweep steps for that repetition, indicating a
        mismatch between acquisition and the sweep configuration.

        Args:
            ctx: Shared execution environment providing access to settings
                and the logger.
            jobs: Job manager to which sharpness evaluation callables are
                submitted for asynchronous execution.
            image: The full image acquired during the sweep, containing
                horizontal stripes separated by dark bands.
            sweep_steps: Pre-generated list of sweep steps, shared with
                `_variable_sweeping_during_scan` to ensure consistency.

        Raises:
            AutofunctionError: If the number of rows in a stripe does not match
                the number of sweep steps for that repetition.
        """
        mode = ctx.settings.mode
        assert isinstance(mode, LineModeSettings)

        forbidden_stripes = mode.forbidden_stripe_indices
        separator_threshold = mode.stripe_separator_threshold
        min_stripe_width = mode.minimal_stripe_width

        # convert the image to 8-bit for stripe detection
        img_8bit = image.to_8bit()

        # identify stripes from the image;
        # each stripe corresponds to one sweeping repetition
        stripes = get_stripes(img_8bit, separator_threshold, min_stripe_width)

        # group sweep steps by repetition to match against stripes
        sweep_groups = groupby(sweep_steps, key=lambda step: step.repetition)

        for stripe, (rep, steps_iter) in zip(stripes, sweep_groups):
            if rep in forbidden_stripes:
                continue

            steps = list(steps_iter)

            # sanity check: stripe must have exactly the same number of rows
            # as sweep steps for this repetition
            if len(stripe) != len(steps):
                raise AutofunctionError(
                    f"Stripe length ({len(stripe)}) does not match sweep count ({len(steps)}) for repetition {rep}."
                )

            # submit a sharpness evaluation job for each row of the stripe,
            # matched to its corresponding sweep step by index
            for line_index, step in zip(stripe, steps):
                image_line = image[line_index, :]
                jobs.submit(ctx.make_resolution_job(image_line, step))


"""
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
