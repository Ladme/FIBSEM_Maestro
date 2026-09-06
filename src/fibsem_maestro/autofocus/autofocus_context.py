# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

import contextvars
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import numpy as np

from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.autofocus.error import AutofocusError
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.autofocus_settings import (
    AutofocusSettings,
    AutoscriptMode,
)


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

    @contextmanager
    def temporary_stage_x_offset(self) -> Iterator[None]:
        """
        Temporarily move the stage in X to a nearby focusing area.

        Displaces the stage by `-delta_x` before entering the block and
        restores it by `+delta_x` afterward, regardless of whether the block
        raises an exception.

        Yields:
            None: Control is yielded to the caller with the stage displaced.
        """
        # move the stage away
        self.microscope.move_stage_position_with_verification(
            StagePosition(x=-self.settings.delta_x)
        )
        self.ctx.text_logger.info(
            f"Moving stage to focusing area (X offset {-self.settings.delta_x:+g})"
        )

        try:
            yield
        finally:
            # move the stage back
            self.microscope.move_stage_position_with_verification(
                StagePosition(x=self.settings.delta_x)
            )
            self.ctx.text_logger.info(
                f"Restoring stage position (X offset {self.settings.delta_x:+g})"
            )

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
        current_view = self.ctx.current_view
        text_logger = self.ctx.text_logger.at(current_view.slice_index)
        image_logger = self.ctx.image_logger.at(current_view.slice_index)

        def fn() -> AutofocusResult:
            def _run() -> AutofocusResult:
                try:
                    assert not isinstance(self.settings.mode, AutoscriptMode)
                    criterion = Criterion(
                        self.settings.mode.criterion,
                        text_logger,
                        image_logger,
                    )
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
