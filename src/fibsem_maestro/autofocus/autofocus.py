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
from fibsem_maestro.microscope.autoscript_control.microscope_control import (
    AutoscriptMicroscopeControl,
)
from fibsem_maestro.settings.autofunction_settings import LineMode as LineModeSettings

if TYPE_CHECKING:
    from collections.abc import Generator

    from autoscript_sdb_microscope_client.sdb_microscope_client import (
        SdbMicroscopeClient,
    )

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
                    f"Autofunction step {sweep.index + 1} "
                    f"(repetition {sweep.repetition + 1}): value {sweep.value}"
                )
                ctx.sweeping.set_attribute_value(sweep.value)
                image = ctx.microscope.beam.grab_frame()
                jobs.submit(ctx.make_sharpness_job(image, sweep))

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
                ctx.txt_log.info(f"Line sweep cycle {repetition + 1}.")

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
                jobs.submit(ctx.make_sharpness_job(image_line, step))


@AutofocusRegistry.register("step")
class StepMode(AutofocusMode):
    """
    Autofocus mode that spreads a parameter sweep across consecutive slices.

    Instead of acquiring its own images, this mode uses the main acquisition
    loop: each slice's production image serves as one trial in the sweep.
    This avoids extra exposure and throughput overhead, at the cost of
    spreading a single autofocus run over many slices.

    On each tick (one per slice) the mode advances the sweep by one step,
    setting the attribute value that the upcoming acquisition will use.
    The image acquired at that value is scored on the following tick, once
    it becomes available from the main loop. After the final step, one
    trailing tick is needed to score the last acquired image before the
    best value can be selected.
    """

    def execute(
        self, ctx: AutofunctionContext, jobs: JobsManager
    ) -> Generator[None, None, None]:
        previous_step: SweepStep | None = None

        for sweep in ctx.sweeping.sweep():
            ctx.txt_log.info(
                f"Autofunction step {sweep.index + 1} "
                f"(repetition {sweep.repetition + 1}): value {sweep.value}"
            )

            # score the image from the previous slice, taken at the previous step's value
            # this is skipped on the first tick
            if previous_step is not None:
                if (image := ctx.imaging.last_acquired_image) is None:
                    ctx.txt_log.warning(
                        f"Last acquired image is not available for {ctx.imaging.name}. "
                        "Skipping sharpness evaluation for this sweep."
                    )
                else:
                    jobs.submit(ctx.make_sharpness_job(image, previous_step))

            # set the value that the upcoming acquisition will use
            ctx.sweeping.set_attribute_value(sweep.value)

            previous_step = sweep
            yield

        # trailing tick: score the image acquired at the final step's value
        assert previous_step is not None
        if (image := ctx.imaging.last_acquired_image) is None:
            ctx.txt_log.warning(
                f"Last acquired image is not available for {ctx.imaging.name}. "
                "Skipping sharpness evaluation for this sweep."
            )
        else:
            jobs.submit(ctx.make_sharpness_job(image, previous_step))


@AutofocusRegistry.register("autoscript")
class AutoscriptMode(AutofocusMode):
    """
    Autofocus mode that delegates to the Autoscript manufacturer routines.

    Executes the appropriate built-in autofunction (autofocus, autostigmator,
    lens alignment, or source tilt correction) based on the configured sweep
    attribute. The stage is temporarily displaced to a nearby focusing area
    for the duration of the operation.

    Raises:
        AutofunctionError: If the microscope is not Autoscript-controlled, or
            if the sweep attribute is not supported.
    """

    def execute(
        self, ctx: AutofunctionContext, jobs: JobsManager
    ) -> Generator[None, None, None]:
        """
        Execute the manufacturer autofunction for the configured sweep attribute.

        Args:
            ctx: Shared execution environment providing access to the
                microscope, sweeping controller, and logger.
            jobs: Unused in this mode - manufacturer autofunctions do not
                submit sharpness jobs.

        Raises:
            AutofunctionError: If the microscope is not Autoscript-controlled,
                or if the sweep attribute is not supported.
        """

        _ = jobs

        if not isinstance(ctx.microscope.control, AutoscriptMicroscopeControl):
            raise AutofunctionError(
                "Microscope must be an Autoscript-controlled microscope."
            )

        autoscript_microscope: SdbMicroscopeClient = (
            ctx.microscope.control.autoscript_microscope  # type: ignore
        )

        with ctx.temporary_stage_x_offset():
            match ctx.sweeping.sweep_attribute:
                case "working_distance":
                    self._run_autofocus(ctx, autoscript_microscope)
                case "stigmator":
                    self._run_autostigmator(ctx, autoscript_microscope)
                case "lens_alignment":
                    self._run_auto_lens_alignment(ctx, autoscript_microscope)
                case "source_tilt":
                    self._run_auto_source_tilt(ctx, autoscript_microscope)
                case _:
                    raise AutofunctionError(
                        f"Unsupported sweeping variable '{ctx.sweeping.sweep_attribute}' for AutoscriptMode."
                    )

        yield from ()

    def _run_autofocus(
        self,
        ctx: AutofunctionContext,
        autoscript_microscope: SdbMicroscopeClient,
    ) -> None:
        """
        Run the manufacturer autofocus routine.

        Args:
            ctx: Shared execution environment.
            autoscript_microscope: The Autoscript microscope client instance.
        """
        from autoscript_sdb_microscope_client.structures import RunAutoFocusSettings

        beam = ctx.microscope.beam
        if (scanning_area := beam.scanning_area).is_full_frame():
            settings = RunAutoFocusSettings()
        else:
            settings = RunAutoFocusSettings(reduced_area=scanning_area.to_autoscript())

        autoscript_microscope.auto_functions.run_auto_focus(settings)

    def _run_autostigmator(
        self,
        ctx: AutofunctionContext,
        autoscript_microscope: SdbMicroscopeClient,
    ) -> None:
        """
        Run the manufacturer autostigmator routine.

        Uses the OngEtAl method with the beam's current imaging parameters.

        Args:
            ctx: Shared execution environment.
            autoscript_microscope: The Autoscript microscope client instance.
        """
        from autoscript_sdb_microscope_client.structures import RunAutoStigmatorSettings

        beam = ctx.microscope.beam
        settings = RunAutoStigmatorSettings(
            method="OngEtAl",
            dwell_time=beam.dwell_time,
            resolution=str(beam.resolution),
            horizontal_field_width=beam.horizontal_field_width * 1e-9,
            reduced_area=beam.scanning_area.to_autoscript(),
            line_integration=beam.line_integration,
        )

        autoscript_microscope.auto_functions.run_auto_stigmator(settings)

    def _run_auto_lens_alignment(
        self,
        ctx: AutofunctionContext,
        autoscript_microscope: SdbMicroscopeClient,
    ) -> None:
        """
        Run the manufacturer lens alignment routine.

        Args:
            ctx: Shared execution environment.
            autoscript_microscope: The Autoscript microscope client instance.
        """
        from autoscript_sdb_microscope_client.structures import (
            RunAutoLensAlignmentSettings,
        )

        beam = ctx.microscope.beam
        if (scanning_area := beam.scanning_area).is_full_frame():
            settings = RunAutoLensAlignmentSettings(
                dwell_time=beam.dwell_time,
                resolution=str(beam.resolution),
                line_integration=beam.line_integration,
            )
        else:
            settings = RunAutoLensAlignmentSettings(
                dwell_time=beam.dwell_time,
                resolution=str(beam.resolution),
                line_integration=beam.line_integration,
                reduced_area=scanning_area.to_autoscript(),
            )

        autoscript_microscope.auto_functions.run_auto_lens_alignment(settings)

    def _run_auto_source_tilt(
        self,
        ctx: AutofunctionContext,
        autoscript_microscope: SdbMicroscopeClient,
    ) -> None:
        """
        Run the manufacturer source tilt correction routine.

        Temporarily switches the detector to TLD in secondary electron mode,
        which is required by the Volumescope source tilt method. The original
        detector settings are restored afterward, even if the routine raises.

        Args:
            ctx: Shared execution environment.
            autoscript_microscope: The Autoscript microscope client instance.
        """
        from autoscript_sdb_microscope_client.enumerations import DetectorMode
        from autoscript_sdb_microscope_client.structures import (
            RunAutoSourceTiltSettings,
        )

        beam = ctx.microscope.beam
        settings = RunAutoSourceTiltSettings(
            method="Volumescope",
            contrast=beam.detector_contrast,
            brightness=beam.detector_brightness,
            dwell_time=beam.dwell_time,
        )

        detector_type_backup = autoscript_microscope.detector.type.value
        detector_mode_backup = autoscript_microscope.detector.mode.value
        autoscript_microscope.detector.type.value = "TLD"
        autoscript_microscope.detector.mode.value = DetectorMode.SECONDARY_ELECTRONS
        try:
            autoscript_microscope.auto_functions.run_auto_source_tilt(settings)
        finally:
            autoscript_microscope.detector.type.value = detector_type_backup
            autoscript_microscope.detector.mode.value = detector_mode_backup
