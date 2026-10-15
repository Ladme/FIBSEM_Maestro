# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import contextvars
from collections.abc import Callable

import numpy as np

from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.autofocus.error import AutofocusError
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.image import Image
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.autofocus_settings import (
    AutofocusSettings,
    CustomCriterion,
    ImagingCriterion,
)
from fibsem_maestro.settings.autofocus_settings import BasicMode as BasicModeSettings
from fibsem_maestro.settings.autofocus_settings import LineMode as LineModeSettings
from fibsem_maestro.settings.autofocus_settings import StepMode as StepModeSettings
from fibsem_maestro.settings.criterion_settings import CriterionSettings


class AutofocusContext:
    def __init__(
        self,
        microscope: Microscope,
        target_attribute: str,
        sweeping: Sweeping | None,
        settings: AutofocusSettings,
        ctx: ActionContext,
    ):
        """
        Shared execution environment for autofocus mode implementations.

        Args:
            microscope: The microscope instance.
            target_attribute: Attribute which is optimized during autofocus.
            sweeping: Controller for sweeping the target beam attribute.
            settings: Autofocus configuration.
            ctx: Context providing slice navigation and access logging and storage.
        """
        self.microscope = microscope
        self.target_attribute = target_attribute
        self.sweeping = sweeping
        self.ctx = ctx
        self.settings = settings

        # the frame a line-mode sweep was evaluated on, kept for logging after the sweep
        self.line_focus_image: Image | None = None

    def make_sharpness_job(
        self, image: Image, sweep: SweepStep
    ) -> Callable[[], AutofocusResult]:
        """
        Create a callable that computes sharpness for a single sweep step.

        The returned callable is intended to be submitted to a `JobsManager`
        for asynchronous execution in a thread pool. It evaluates image
        sharpness using the configured criterion and packages the result
        together with the associated sweep step.

        The logging and store context is captured at the time this method is
        called, so the job always writes to the slice that was active at
        creation time, regardless of what the main thread does subsequently.

        If sharpness calculation raises an exception or returns NaN, a warning
        is logged and the exception is re-raised so that `JobsManager` can
        exclude the failed job from the collected results.

        Args:
            image: The image acquired at this sweep step.
            sweep: The sweep step associated with this image.

        Returns:
            A zero-argument callable that returns an `AutofocusResult` when
            invoked, or raises an exception if sharpness calculation fails
            or if the criterion is not defined.
        """
        ctx_snapshot = contextvars.copy_context()
        criterion_settings = self.criterion
        current_view = self.ctx.current_view
        text_logger = self.ctx.text_logger.at(current_view.slice_index)
        image_logger = self.ctx.image_logger.at(current_view.slice_index)

        def fn() -> AutofocusResult:
            def _run() -> AutofocusResult:
                try:
                    criterion = Criterion(criterion_settings, text_logger, image_logger)
                    value = float(criterion.calculate_sharpness(image))
                    if np.isnan(value):
                        raise AutofocusError("Sharpness calculation returned NaN")
                    text_logger.info(
                        f"Sharpness calculation for sweep {sweep}: {value}"
                    )
                    return AutofocusResult(value, sweep)
                except Exception as exc:
                    text_logger.warning(
                        f"Sharpness calculation for sweep {sweep.value} failed: {exc}."
                    )
                    raise

            return ctx_snapshot.run(_run)

        return fn

    @property
    def scanning_area(self) -> RelativeArea | None:
        """
        The area the configured mode scans during its sweep.

        Returns:
            The basic or line mode's scanning area, or None to leave the beam's
            current scanning area unchanged (no area set, or another mode).
        """
        match self.settings.mode:
            case BasicModeSettings() | LineModeSettings() as mode if mode.scanning_area:
                return mode.scanning_area[0]
            case _:
                return None

    @property
    def criterion(self) -> CriterionSettings:
        """
        The criterion the autofocus scores frames with.

        Raises:
            AutofocusError: If the configured mode has no criterion of its own
                (Autoscript, or step mode using the imaging's criterion).
        """
        match self.settings.mode:
            case BasicModeSettings() | LineModeSettings() as mode:
                return mode.criterion
            case StepModeSettings(criterion=CustomCriterion() as custom):
                return custom.criterion
            case _:
                raise AutofocusError("The autofocus mode has no criterion of its own.")

    @property
    def uses_imaging_criterion(self) -> bool:
        """True if step mode reuses the sharpness its linked imaging calculates."""
        mode = self.settings.mode

        return isinstance(mode, StepModeSettings) and isinstance(
            mode.criterion, ImagingCriterion
        )
