# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from itertools import groupby
from typing import TYPE_CHECKING

import numpy as np

from fibsem_maestro.autofocus.error import AutofocusError
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.core.image_tools import get_stripes
from fibsem_maestro.core.registry import Registry
from fibsem_maestro.microscope.autoscript_control.microscope_control import (
    AutoscriptMicroscopeControl,
)
from fibsem_maestro.settings.autofocus_settings import (
    AutoscriptAutoFocus,
    AutoscriptAutoFocusMethod,
    AutoscriptAutoLensAlignment,
    AutoscriptAutoLensAlignmentModulationType,
    AutoscriptAutoSourceTilt,
    AutoscriptAutoStigmator,
    AutoscriptAutoStigmatorMethod,
)
from fibsem_maestro.settings.autofocus_settings import LineMode as LineModeSettings

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator

    from autoscript_sdb_microscope_client.sdb_microscope_client import (
        SdbMicroscopeClient,
    )

    from fibsem_maestro.autofocus.autofocus_context import AutofocusContext
    from fibsem_maestro.autofocus.jobs_manager import JobsManager
    from fibsem_maestro.core.image import Image
    from fibsem_maestro.imaging.imaging import Imaging

# registry of autofocus modes
AUTOFOCUS_MODES = Registry[type["AutofocusMode"]]("autofocus mode")


class AutofocusMode(ABC):
    """
    Abstract base class for autofocus mode implementations.

    Each subclass encodes a specific strategy for sweeping a beam parameter
    and submitting sharpness evaluation jobs. Concrete modes are registered
    with `AutofocusRegistry` and retrieved by name at runtime.
    """

    @abstractmethod
    def execute(
        self,
        ctx: AutofocusContext,
        jobs: JobsManager,
        imaging: Imaging | None,
        resume_from: int = 0,
    ) -> Generator[None, None, None]:
        """
        Drive the autofocus sweep and submit sharpness evaluation jobs.

        Args:
            ctx: Shared execution environment providing access to the
                microscope, sweeping controller, criterion, and logger.
            jobs: Job manager to which sharpness evaluation callables are
                submitted for asynchronous execution.
            imaging: Instance of the Imaging class used to acquire images.
            resume_from: Global index of the sweep to resume from (default 0).
                Only used by the StepMode.
        """


@AUTOFOCUS_MODES.register("basic")
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
        self,
        ctx: AutofocusContext,
        jobs: JobsManager,
        imaging: Imaging | None,
        resume_from: int = 0,
    ) -> Generator[None, None, None]:
        _ = imaging, resume_from

        if (sweeping := ctx.sweeping) is None:
            raise AutofocusError("Sweeping for basic mode autofocus is not defined.")

        with ctx.temporary_stage_x_offset():
            for sweep in sweeping.sweep():
                ctx.ctx.text_logger.info(
                    f"Autofunction step {sweep.index + 1} "
                    f"(repetition {sweep.repetition + 1}): value {sweep.value}"
                )
                sweeping.set_attribute_value(sweep.value)
                image = ctx.microscope.beam.grab_frame()
                jobs.submit(ctx.make_sharpness_job(image, sweep))

        yield from ()


@AUTOFOCUS_MODES.register("line")
class LineMode(AutofocusMode):
    def execute(
        self,
        ctx: AutofocusContext,
        jobs: JobsManager,
        imaging: Imaging | None,
        resume_from: int = 0,
    ) -> Generator[None, None, None]:
        _ = imaging, resume_from

        if (sweeping := ctx.sweeping) is None:
            raise AutofocusError("Sweeping for line mode autofocus is not defined.")

        with ctx.temporary_stage_x_offset():
            line_time = self._estimate_line_time(ctx)

            # generate sweep steps once so both acquisition and processing see the same steps
            sweep_steps = list(sweeping.sweep())

            self._variable_sweeping_during_scan(ctx, line_time, sweep_steps)

            line_focus_image = ctx.microscope.beam.get_image()
            self._process_image(ctx, jobs, line_focus_image, sweep_steps)

        yield from ()

    def _estimate_line_time(self, ctx: AutofocusContext) -> float:
        """
        Estimate the time required to scan a single line.

        Args:
            ctx: Shared execution environment providing access to the microscope
                and beam parameters.

        Returns:
            Estimated line scan time in seconds with line time correction factor applied.
        """
        mode = ctx.settings.mode
        assert isinstance(mode, LineModeSettings)
        dwell_time = ctx.microscope.beam.dwell_time
        line_integration = ctx.microscope.beam.line_integration
        resolution = ctx.microscope.beam.resolution
        scanning_area = ctx.microscope.beam.scanning_area
        correction_factor = mode.line_time_correction_factor

        estimated_line_time = (
            # time spent per pixel
            dwell_time
            # length of the full row in pixels
            * resolution.width
            # portion of the line actually scanned
            * scanning_area.width
            # number of times each row is scanned
            * line_integration
            # user-defined factor accounting for microscope delays
            * correction_factor
        )

        ctx.ctx.text_logger.debug(f"Estimated line time: {estimated_line_time} s")

        return estimated_line_time

    def _variable_sweeping_during_scan(
        self,
        ctx: AutofocusContext,
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
        assert ctx.sweeping is not None

        pre_delay = mode.pre_imaging_delay
        hold = mode.lines_per_sweep * line_time

        ctx.microscope.beam.start_acquisition()
        try:
            # group consecutive sweep steps by repetition index so that each
            # cycle produces one stripe in the acquired image
            for repetition, steps in groupby(sweep_steps, key=lambda x: x.repetition):
                ctx.ctx.text_logger.info(f"Line sweep cycle {repetition + 1}.")

                # blank to create a dark separator band between the stripes
                with ctx.microscope.beam.total_blanked():
                    if repetition == 0 and pre_delay > 0:
                        time.sleep(pre_delay)
                    time.sleep(hold)

                # acquire part of the stripe with each sweep value
                for sweep in steps:
                    ctx.sweeping.set_attribute_value(sweep.value)
                    time.sleep(hold)

            # create a final dark separator band
            with ctx.microscope.beam.total_blanked():
                time.sleep(hold)

        finally:
            ctx.microscope.beam.stop_acquisition()

    def _process_image(
        self,
        ctx: AutofocusContext,
        jobs: JobsManager,
        image: Image,
        sweep_steps: list[SweepStep],
    ) -> None:
        """
        Extract per-line sharpness jobs from the acquired image.

        Identifies horizontal stripes in the image using dark separator rows
        produced by blanking during acquisition. Each stripe corresponds to one
        sweep cycle (repetition). Within each stripe, the rows are split into
        equal sub-groups - one per sweep step in that repetition. Each line
        within a sub-group is evaluated independently, producing multiple
        sharpness measurements per sweep step value.

        Stripes listed in `forbidden_stripe_indices` are skipped entirely.

        Args:
            ctx: Shared execution environment providing access to settings
                and the logger.
            jobs: Job manager to which sharpness evaluation callables are
                submitted for asynchronous execution.
            image: The full image acquired during the sweep, containing
                horizontal stripes separated by dark bands.
            sweep_steps: Pre-generated list of sweep steps, shared with
                `_variable_sweeping_during_scan` to ensure consistency.
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

            # split lines of one stripe into equal sub-groups
            # each group then corresponds to one value of the sweep variable
            sub_bins = np.array_split(stripe, len(steps))

            # submit a sharpness job for each line within each sub-bin
            # associating all lines in the sub-bin with their corresponding sweep step
            for step, sub_bin in zip(steps, sub_bins):
                for line_index in sub_bin:
                    image_line = image[line_index, :]

                    # create a new SweepStep containing row index
                    step_with_line_index = SweepStep(
                        repetition=step.repetition,
                        value=step.value,
                        index=step.index,
                        line_index=int(line_index),
                    )
                    jobs.submit(
                        ctx.make_sharpness_job(image_line, step_with_line_index)
                    )


@AUTOFOCUS_MODES.register("step")
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
        self,
        ctx: AutofocusContext,
        jobs: JobsManager,
        imaging: Imaging | None,
        resume_from: int = 0,
    ) -> Generator[None, None, None]:
        if not imaging:
            raise AutofocusError(
                "Linking imaging to autofocus is required for step mode autofocus."
            )

        if (sweeping := ctx.sweeping) is None:
            raise AutofocusError("Sweeping for step mode autofocus is not defined.")
        previous_step: SweepStep | None = None

        for sweep in sweeping.sweep():
            # skip steps before the resume point
            if sweep.index < resume_from:
                ctx.ctx.text_logger.debug(
                    f"Skipping step {sweep.index + 1} (repetition {sweep.repetition + 1}) before resume point."
                )
                previous_step = sweep
                continue

            ctx.ctx.text_logger.info(
                f"Autofunction step {sweep.index + 1} "
                f"(repetition {sweep.repetition + 1}): value {sweep.value}"
            )

            # score the image from the previous slice, taken at the previous step's value
            # this is skipped on the first tick
            if previous_step is not None:
                if (image := imaging.last_acquired_image) is None:
                    ctx.ctx.text_logger.warning(
                        f"Last acquired image is not available for {imaging.name}. "
                        "Skipping sharpness evaluation for this sweep."
                    )
                else:
                    jobs.submit(ctx.make_sharpness_job(image, previous_step))

            # set the value that the upcoming acquisition will use
            sweeping.set_attribute_value(sweep.value)

            previous_step = sweep
            yield

        # trailing tick: score the image acquired at the final step's value
        assert previous_step is not None
        if (image := imaging.last_acquired_image) is None:
            ctx.ctx.text_logger.warning(
                f"Last acquired image is not available for {imaging.name}. "
                "Skipping sharpness evaluation for this sweep."
            )
        else:
            jobs.submit(ctx.make_sharpness_job(image, previous_step))


@AUTOFOCUS_MODES.register("autoscript")
class AutoscriptMode(AutofocusMode):
    """
    Autofocus mode that delegates to the Autoscript manufacturer routines.

    Executes the appropriate built-in autofunction (autofocus, autostigmator,
    lens alignment, or source tilt correction) based on the configured sweep
    attribute. The stage is temporarily displaced to a nearby focusing area
    for the duration of the operation.

    Raises:
        AutofocusError: If the microscope is not Autoscript-controlled, or
            if the sweep attribute is not supported.
    """

    def execute(
        self,
        ctx: AutofocusContext,
        jobs: JobsManager,
        imaging: Imaging | None,
        resume_from: int = 0,
    ) -> Generator[None, None, None]:
        _ = jobs, imaging, resume_from

        if not isinstance(ctx.microscope.control, AutoscriptMicroscopeControl):
            raise AutofocusError(
                "Microscope must be an Autoscript-controlled microscope."
            )

        autoscript_microscope: SdbMicroscopeClient = (
            ctx.microscope.control.autoscript_microscope
        )

        with ctx.temporary_stage_x_offset():
            match ctx.settings.mode:
                case AutoscriptAutoFocus() as mode:
                    self._run_autofocus(ctx, mode, autoscript_microscope)
                case AutoscriptAutoStigmator() as mode:
                    self._run_autostigmator(ctx, mode, autoscript_microscope)
                case AutoscriptAutoLensAlignment() as mode:
                    self._run_auto_lens_alignment(ctx, mode, autoscript_microscope)
                case AutoscriptAutoSourceTilt() as mode:
                    self._run_auto_source_tilt(ctx, mode, autoscript_microscope)
                case _:
                    raise AutofocusError(
                        f"Unsupported mode '{ctx.settings.mode}' for AutoscriptMode."
                    )

        yield from ()

    def _run_autofocus(
        self,
        ctx: AutofocusContext,
        mode: AutoscriptAutoFocus,
        autoscript_microscope: SdbMicroscopeClient,
    ) -> None:
        """
        Run the manufacturer autofocus routine.

        Args:
            ctx: Shared execution environment.
            mode: The Autoscript auto focus mode settings.
            autoscript_microscope: The Autoscript microscope client instance.
        """
        from autoscript_sdb_microscope_client.structures import RunAutoFocusSettings

        beam = ctx.microscope.beam
        if (scanning_area := beam.scanning_area).is_full_frame():
            reduced_area = None
        else:
            reduced_area = scanning_area.to_autoscript()

        match mode.method:
            case AutoscriptAutoFocusMethod.STANDARD:
                settings = RunAutoFocusSettings(
                    reduced_area=reduced_area  # ty:ignore[invalid-argument-type]
                )
            case AutoscriptAutoFocusMethod.VOLUMESCOPE:
                # TODO: shouldn't volumescope use secondary electrons?

                wd_step_as = (
                    mode.working_distance_step * 1e-9
                    if mode.working_distance_step is not None
                    else None
                )
                settings = RunAutoFocusSettings(
                    method="Volumescope",
                    dwell_time=beam.dwell_time,
                    horizontal_field_width=beam.horizontal_field_width * 1e-9,
                    line_integration=beam.line_integration,
                    resolution=str(beam.resolution),
                    # None is a valid value for all these fields
                    # Autoscript is just badly typed
                    reduced_area=reduced_area,  # ty:ignore[invalid-argument-type]
                    maximum_iterations=mode.maximum_iterations,  # ty:ignore[invalid-argument-type]
                    working_distance_step=wd_step_as,  # ty:ignore[invalid-argument-type]
                )

        autoscript_microscope.auto_functions.run_auto_focus(settings)

    def _run_autostigmator(
        self,
        ctx: AutofocusContext,
        mode: AutoscriptAutoStigmator,
        autoscript_microscope: SdbMicroscopeClient,
    ) -> None:
        """
        Run the manufacturer autostigmator routine.

        Args:
            ctx: Shared execution environment.
            mode: The Autoscript auto stigmator mode settings.
            autoscript_microscope: The Autoscript microscope client instance.
        """
        from autoscript_sdb_microscope_client.structures import RunAutoStigmatorSettings

        beam = ctx.microscope.beam
        if (scanning_area := beam.scanning_area).is_full_frame():
            reduced_area = None
        else:
            reduced_area = scanning_area.to_autoscript()

        match mode.method:
            case AutoscriptAutoStigmatorMethod.STANDARD:
                settings = RunAutoStigmatorSettings()
            case AutoscriptAutoStigmatorMethod.ONGETAL:
                settings = RunAutoStigmatorSettings(
                    method="OngEtAl",
                    dwell_time=beam.dwell_time,
                    resolution=str(beam.resolution),
                    horizontal_field_width=beam.horizontal_field_width * 1e-9,
                    line_integration=beam.line_integration,
                    # None is a valid value for all these fields
                    reduced_area=reduced_area,  # ty:ignore[invalid-argument-type]
                    maximum_iterations=mode.maximum_iterations,  # ty:ignore[invalid-argument-type]
                    stigmation_step=mode.stigmation_step,  # ty:ignore[invalid-argument-type]
                )

        autoscript_microscope.auto_functions.run_auto_stigmator(settings)

    def _run_auto_lens_alignment(
        self,
        ctx: AutofocusContext,
        mode: AutoscriptAutoLensAlignment,
        autoscript_microscope: SdbMicroscopeClient,
    ) -> None:
        """
        Run the manufacturer lens alignment routine.

        Args:
            ctx: Shared execution environment.
            mode: The Autoscript auto lens alignment mode settings.
            autoscript_microscope: The Autoscript microscope client instance.
        """
        from autoscript_sdb_microscope_client.structures import (
            RunAutoLensAlignmentSettings,
        )

        beam = ctx.microscope.beam
        if (scanning_area := beam.scanning_area).is_full_frame():
            reduced_area = None
        else:
            reduced_area = scanning_area.to_autoscript()

        match mode.modulation_type:
            case AutoscriptAutoLensAlignmentModulationType.AUTOMATIC:
                modulation_type_as = "Automatic"
            case AutoscriptAutoLensAlignmentModulationType.HIGH_VOLTAGE:
                modulation_type_as = "HighVoltage"
            case AutoscriptAutoLensAlignmentModulationType.WORKING_DISTANCE:
                modulation_type_as = "WorkingDistance"

        settings = RunAutoLensAlignmentSettings(
            modulation_type=modulation_type_as,
            dwell_time=beam.dwell_time,
            resolution=str(beam.resolution),
            line_integration=beam.line_integration,
            # None is a valid value for all these fields
            reduced_area=reduced_area,  # ty:ignore[invalid-argument-type]
            number_of_frames=mode.number_of_frames,  # ty:ignore[invalid-argument-type]
        )

        autoscript_microscope.auto_functions.run_auto_lens_alignment(settings)

    def _run_auto_source_tilt(
        self,
        ctx: AutofocusContext,
        mode: AutoscriptAutoSourceTilt,
        autoscript_microscope: SdbMicroscopeClient,
    ) -> None:
        """
        Run the manufacturer source tilt correction routine.

        Temporarily switches the detector to TLD in secondary electron mode,
        which is required by the Volumescope source tilt method. The original
        detector settings are restored afterward, even if the routine raises.

        Args:
            ctx: Shared execution environment.
            mode: The Autoscript auto source tilt mode settings.
            autoscript_microscope: The Autoscript microscope client instance.
        """
        from autoscript_sdb_microscope_client.structures import (
            RunAutoSourceTiltSettings,
        )

        _ = mode

        beam = ctx.microscope.beam
        settings = RunAutoSourceTiltSettings(
            method="Volumescope",
            contrast=beam.detector_contrast,
            brightness=beam.detector_brightness,
            dwell_time=beam.dwell_time,
            resolution=str(beam.resolution),
        )

        with self._secondary_electrons(autoscript_microscope):
            autoscript_microscope.auto_functions.run_auto_source_tilt(settings)

    @staticmethod
    @contextmanager
    def _secondary_electrons(
        microscope: SdbMicroscopeClient,
    ) -> Iterator[None]:
        """
        Temporarily switch the detector to TLD in secondary electron mode, restoring it on exit.

        Args:
            microscope: Autoscript microscope client.

        Yields:
            None. The original detector settings are restored even if the body raises.
        """
        from autoscript_sdb_microscope_client.enumerations import DetectorMode

        type_backup = microscope.detector.type.value
        mode_backup = microscope.detector.mode.value
        microscope.detector.type.value = "TLD"
        microscope.detector.mode.value = DetectorMode.SECONDARY_ELECTRONS
        try:
            yield
        finally:
            microscope.detector.type.value = type_backup
            microscope.detector.mode.value = mode_backup
