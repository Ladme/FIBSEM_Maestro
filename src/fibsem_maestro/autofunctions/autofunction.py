# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import contextlib
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any

import numpy as np

from fibsem_maestro.autofunctions.autofocus import AutofocusStatus
from fibsem_maestro.autofunctions.autofocus_registry import AutofocusRegistry
from fibsem_maestro.autofunctions.error import AutofunctionError
from fibsem_maestro.autofunctions.result import AutofocusResult
from fibsem_maestro.autofunctions.sweep_step import SweepStep
from fibsem_maestro.autofunctions.sweeping import Sweeping
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.image_criteria.criterion import Criterion
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.autofunction_settings import AutofunctionSettings
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.mask_settings import MaskSettings
from fibsem_maestro.settings.reactive import ReactiveDict


class Autofunction:
    def __init__(
        self,
        name: str,
        settings: AutofunctionSettings,
        microscope: Microscope,
        criteria: ReactiveDict[str, CriterionSettings],
        imaging: ReactiveDict[str, ImagingSettings],
        masks: ReactiveDict[str, MaskSettings],
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._name = name
        self._txt_log = txt_log
        self._img_log = img_log

        self._criteria = criteria
        self._masks = masks
        self._imagings = imaging
        self._microscope = microscope

        self._criterion_name = None
        self._imaging_name = None
        self._mask_name = None

        self._apply_settings(settings)
        self._settings.on_change(self._update)

        self._sweeping = Sweeping(
            self._microscope._control,
            self._settings.sweeping,
            self._txt_log.derive("sweeping"),
        )

        # async calculation of image resolutions
        self._executor = ThreadPoolExecutor(max_workers=self._settings.max_workers)
        self._pending: list[Future[np.floating[Any]]] = []
        self._pending_lock = threading.Lock()

        self._results: list[AutofocusResult] = []
        self._results_lock = threading.Lock()

    def _update(self, settings: AutofunctionSettings) -> None:
        self._apply_settings(settings)

    def _set_criterion(self, criterion_name: str) -> None:
        if criterion_settings := self._criteria.get(criterion_name):
            self._criterion = Criterion(
                criterion_name,
                criterion_settings,
                self._masks,
                self._txt_log.derive(f"criterion {criterion_name}"),
                self._img_log,
            )
            self._criterion_name = criterion_name
        else:
            raise AutofunctionError(f"Criterion '{criterion_name}' does not exist.")

    def _set_imaging(self, imaging_name: str) -> None:
        if imaging_settings := self._imagings.get(imaging_name):
            self._imaging_settings = imaging_settings
            self._imaging_name = imaging_name
        else:
            raise AutofunctionError(
                f"Imaging settings '{imaging_settings}' do not exist."
            )

    def _set_mask(self, mask_name: str) -> None:
        if mask_settings := self._masks.get(mask_name):
            self._mask_settings = mask_settings
            self._mask_name = mask_name
        else:
            raise AutofunctionError(f"Mask settings '{mask_settings}' do not exist.")

    def _apply_settings(self, settings: AutofunctionSettings) -> None:
        """Apply all configurable fields from the given settings object."""
        self._settings = settings

        # set new criterion if the criterion name has changed
        if self._settings.criterion_name != self._criterion_name:
            self._set_criterion(self._settings.criterion_name)

        self._mode = AutofocusRegistry.get(self._settings.mode.type)(
            self, self._settings.mode
        )

        # set new imaging settings if the imaging name has changed
        if self._settings.imaging_name != self._imaging_name:
            self._set_imaging(self._settings.imaging_name)

        # set new mask if the mask name has changed
        if self._settings.mask_name != self._mask_name:
            self._set_mask(self._settings.mask_name)

    def execute(self) -> AutofocusStatus:
        return self._mode.execute()

    def should_execute(self, slice_number: int, image_resolution: float | None) -> bool:
        if (
            self._settings.execute_slices > 0
            and slice_number % self._settings.execute_slices == 0
        ):
            return True

        return (
            image_resolution is not None
            and 0 < self._settings.execute_resolution < image_resolution
        )

    def setup_microscope(self) -> None:
        self._microscope.set_imaging_settings(self._imaging_settings)

    @contextmanager
    def temporary_stage_x_offset(self):
        """
        Temporarily move the stage in X to a nearby focusing area and
        always restore the original position afterward.
        """
        # move the stage away
        self._microscope._control.try_move_stage_position(
            StagePosition(x=-self._settings.delta_x)
        )
        self._txt_log.info(
            f"Moving stage to focusing area (X offset {-self._settings.delta_x:+g})"
        )

        try:
            yield
        finally:
            # move the stage back
            self._microscope._control.try_move_stage_position(
                StagePosition(x=self._settings.delta_x)
            )
            self._txt_log.info(
                f"Restoring stage position (X offset {self._settings.delta_x:+g})"
            )

    def submit_resolution_job(self, image: Image, sweep: SweepStep) -> None:
        future = self._executor.submit(self._criterion.calculate_resolution, image)

        with self._pending_lock:
            self._pending.append(future)

        def _done_callback(f: Future[np.floating]) -> None:
            try:
                resolution = float(f.result())
            except Exception as e:
                self._txt_log.warning(
                    f"Resolution calculation for sweep {sweep.value} failed: {e}"
                )
                return

            with self._results_lock:
                self._results.append(AutofocusResult(resolution, sweep))

            self._txt_log.info(f"Resolution for sweep {sweep}: {resolution}")

        future.add_done_callback(_done_callback)

    def wait_for_resolution_jobs(self) -> None:
        while True:
            with self._pending_lock:
                if not self._pending:
                    return
                pending = self._pending
                self._pending = []

            for f in pending:
                # already logged in callback; swallow to drain all futures
                with contextlib.suppress(Exception):
                    f.result()

    def evaluate_best_sweep(self) -> float:
        with self._results_lock:
            return self._sweeping.evaluate_best_sweep(self._results)

    def clear_results(self) -> None:
        with self._results_lock:
            self._results = []

    @property
    def imaging_settings(self) -> ImagingSettings:
        return self._imaging_settings

    @property
    def autofunction_settings(self) -> AutofunctionSettings:
        return self._settings

    @property
    def microscope(self) -> Microscope:
        return self._microscope

    @property
    def criterion(self) -> Criterion:
        return self._criterion

    @property
    def sweeping(self) -> Sweeping:
        return self._sweeping

    @property
    def txt_log(self) -> TextLogger:
        return self._txt_log

    @property
    def img_log(self) -> ImageLogger:
        return self._img_log
