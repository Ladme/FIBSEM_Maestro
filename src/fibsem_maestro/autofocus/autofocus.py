# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import field
from typing import TYPE_CHECKING, Any, Literal

import numpy as np

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.outcome import Produced, StepOutcome
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.autofocus import AUTOFOCUS_MODES, LineMode, StepMode
from fibsem_maestro.autofocus.autofocus_context import AutofocusContext
from fibsem_maestro.autofocus.error import AutofocusError
from fibsem_maestro.autofocus.jobs_manager import JobsManager
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.overlay import PolylineOverlay
from fibsem_maestro.logging.image.plot_element import Curve, PlotElement, VerticalLine
from fibsem_maestro.logging.logging import with_logging_context
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.autofocus_settings import (
    AutofocusSettings,
    AutoscriptFunctionBase,
)
from fibsem_maestro.settings.autofocus_settings import BasicMode as BasicModeSettings
from fibsem_maestro.settings.autofocus_settings import LineMode as LineModeSettings
from fibsem_maestro.settings.autofocus_settings import StepMode as StepModeSettings
from fibsem_maestro.settings.reactive import ChangePath
from fibsem_maestro.workflow.actions import Actions

if TYPE_CHECKING:
    from collections.abc import Generator


class AutofocusState(ActionState):
    sweep_base_value: Any | None = None
    sweep_in_progress: bool = False
    current_step_index: int = 0
    collected_results: list[AutofocusResult] = field(default_factory=list)
    sweeps_done: int = 0
    last_edge: Literal[-1, 1] | None = None


@ACTION_REGISTRY.register("autofocus")
class Autofocus(Action[AutofocusSettings, AutofocusState]):
    """
    Orchestrates the autofocus pipeline for a single configured mode.

    Manages the full autofocus lifecycle: deciding when to execute based on
    slice number and image sharpness, setting up the appropriate mode, advancing
    the execution generator, collecting sharpness results, and writing the best sweep value
    back to the microscope and property store.

    For single-shot modes (basic, line, Autoscript) the sweep completes in a
    single `perform_autofocus` call. For step mode, execution is resumed
    across successive calls, one sweep step per slice, until the sweep is
    exhausted.
    """

    _STATE_FIELDS = frozenset(
        {"mode", "target_attribute", "beam_type", "linked_imaging"}
    )

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: AutofocusSettings,
        ctx: ActionContext,
        actions: Actions,
    ):
        super().__init__(name, microscope, settings, ctx, actions)

        # the pool is sized from max_workers; _reset_jobs resizes it between sweeps
        self._executor_workers = self._settings.max_workers
        self._executor = ThreadPoolExecutor(self._executor_workers)
        self._jobs = JobsManager(executor=self._executor)

        self._active_gen: Generator[SweepStep, None, None] | None = None

        self._sweep_base_value: Any | None = None
        self._current_step_index = 0

        # sweeps completed in the current autofocus run
        self._sweeps_done = 0
        # the edge the best value last reached (-1 lower, 1 upper)
        self._last_edge: Literal[-1, 1] | None = None

        # build mode/sweeping/context from current settings
        self._rebuild()

        # rebuild when the settings they are built from change
        self._settings.on_change_at(self._rebuild_if_affected)

    def _rebuild_if_affected(self, path: ChangePath) -> None:
        """
        Rebuild mode, sweeping and context if a change touched their inputs.

        Args:
            path: Location of the change relative to the settings; an empty path
                means the settings changed as a whole.
        """
        if not path or path[0] in self._STATE_FIELDS:
            self._rebuild()

    def _rebuild(self) -> None:
        """Rebuild mode, sweeping, and autofocus context from current settings."""
        self._mode = AUTOFOCUS_MODES.get(self._settings.mode.type)()

        if isinstance(self._settings.mode, AutoscriptFunctionBase):
            # sweeping is not used in the Autoscript mode
            self._sweeping = None
        else:
            self._sweeping = Sweeping(
                self._microscope.electron_beam
                if self._settings.beam_type is BeamType.ELECTRON
                else self._microscope.ion_beam,
                self._settings.mode.sweeping,
                self._settings.target_attribute,
                self._ctx.text_logger.derive("sweeping"),
            )

        self._autofocus_ctx = AutofocusContext(
            self._microscope,
            self._settings.target_attribute,
            self._sweeping,
            self._settings,
            self._ctx,
        )

    @classmethod
    def settings_cls(cls) -> type[AutofocusSettings]:
        return AutofocusSettings

    @classmethod
    def state_cls(cls) -> type[AutofocusState]:
        return AutofocusState

    @property
    def state(self) -> AutofocusState:
        return AutofocusState(
            sweep_base_value=self._sweep_base_value,
            sweep_in_progress=self._active_gen is not None,
            current_step_index=self._current_step_index,
            collected_results=self._jobs.collect_completed()
            if self._active_gen is not None
            else [],
            sweeps_done=self._sweeps_done,
            last_edge=self._last_edge,
        )

    @property
    def scanning_area(self) -> RelativeArea | None:
        """
        The scanning area of the basic, line or Autoscript mode, if set.

        Step mode has none: its frames come from the linked imaging.
        """
        match self._settings.mode:
            case (
                (
                    BasicModeSettings() | LineModeSettings() | AutoscriptFunctionBase()
                ) as mode
            ) if mode.scanning_area:
                return mode.scanning_area[0]
            case _:
                return None

    def set_state(self, state: AutofocusState) -> None:
        # close a running sweep explicitly
        if self._active_gen is not None:
            self._abort_sweep()

        self._sweep_base_value = state.sweep_base_value
        self._current_step_index = state.current_step_index
        self._sweeps_done = state.sweeps_done
        self._last_edge = state.last_edge

        if not state.sweep_in_progress:
            self._active_gen = None
            return

        self._ctx.text_logger.info(
            f"Restoring state of '{self.name}': sweep in progress, resuming from "
            f"global step index {state.current_step_index}."
        )
        # re-submit collected results so the final wait_and_collect sees them all
        for result in state.collected_results:
            self._jobs.submit(lambda r=result: r)

        self._active_gen = self._mode.execute(
            self._autofocus_ctx,
            self._jobs,
            self._resolve_imaging(),
            resume_from=state.current_step_index,
        )

    def should_execute(self) -> bool:
        """
        Decide whether autofocus runs on the current slice.

        A sweep in progress always continues. Otherwise autofocus runs if the
        slice matches the execution frequency, or if the sharpness of the
        linked imaging's latest frame is below `settings.sharpness_limit`.
        Blocks until that sharpness is available.

        Returns:
            `True` if autofocus should run for this slice.
        """
        if self._active_gen is not None:
            return True

        if self._settings.execution_frequency.matches(self._ctx.slice):
            self._ctx.text_logger.info(
                f"'{self.name}' triggered: slice {self._ctx.slice} matches "
                f"execution frequency ({self._settings.execution_frequency})."
            )
            return True

        if limit := self._settings.sharpness_limit:
            # only wait for sharpness calculation from imaging if we actually need it
            sharpness = self._resolve_imaging().wait_for_sharpness()
            self._ctx.text_logger.debug(f"Last image sharpness: {sharpness}.")

            if sharpness is not None and sharpness < limit:
                self._ctx.text_logger.info(
                    f"'{self.name}' triggered: image sharpness ({sharpness:.4f}) "
                    f"is below the limit ({limit:.4f})."
                )
                return True

        return False

    @with_logging_context
    def test(self) -> None:
        """
        Run the autofocus pipeline once and apply the best sweep value.

        Intended for manual testing and diagnostics outside the normal
        acquisition loop.

        Raises:
            AutofocusError: If the configured mode is a step mode, which spreads
                execution across multiple slices and cannot be run in a single call.
        """
        if isinstance(self._mode, StepMode):
            raise AutofocusError("Test is not supported for step mode")

        self._reset_jobs()

        with self._scanning_area_applied():
            if self._ctx.props_store.exists("props.yaml"):
                self._ctx.text_logger.info("Loading saved microscope properties.")
                self.read_and_set_properties()
            else:
                self._ctx.text_logger.info("No saved microscope properties found.")

            self._run_sweep_and_apply_best()

            # the updated value may not be displayed in the microscope GUI until we start scanning
            self._microscope.beam.grab_frame()

    def wait_for_background_threads(self) -> None:
        self._jobs.wait()

    def _run_step(self) -> StepOutcome:
        if self._active_gen is None:
            self._start_sweep()
        trial = self._advance()

        props = self.collect_properties()
        if trial is None:
            return Produced(props)

        # mid-sweep: the linked imaging must acquire its next frame at the trial value
        patch = GlobalProperties()
        patch.set_property(self._settings.target_attribute, trial.value, self.beam_type)
        return Produced(props, patches={self._settings.linked_imaging: patch})

    def _start_sweep(self) -> None:
        """
        Start a new sweep from the currently applied properties.

        Raises:
            AutofocusError: If step mode is configured with an unsuitable linked imaging.
        """
        # remove the jobs and results of the previous sweep
        # and update the number of workers
        self._reset_jobs()

        imaging = self._resolve_imaging()
        if isinstance(self._mode, StepMode):
            self._check_step_mode_imaging(imaging)

        self._sweep_base_value = (
            self._sweeping.get_attribute_value() if self._sweeping is not None else None
        )
        self._current_step_index = 0
        self._active_gen = self._mode.execute(self._autofocus_ctx, self._jobs, imaging)

    def _check_step_mode_imaging(self, imaging: Imaging) -> None:
        """
        Verify that the linked imaging provides one fresh trial frame per slice.

        Args:
            imaging: The linked imaging action.

        Raises:
            AutofocusError: If the imaging does not run every slice, or uses a
                different beam than the autofocus.
        """
        if not imaging.settings.execution_frequency.runs_every_slice:
            raise AutofocusError(
                f"Step mode requires '{imaging.name}' to run every slice "
                f"(execution frequency 1), got {imaging.settings.execution_frequency}."
            )

        if imaging.beam_type is not self.beam_type:
            raise AutofocusError(
                f"Step mode requires '{imaging.name}' to use the same beam as "
                f"'{self.name}' ({self.beam_type}), got {imaging.beam_type}."
            )

        if (
            self._autofocus_ctx.uses_imaging_criterion
            and imaging.settings.criterion is None
        ):
            raise AutofocusError(
                f"Step mode uses the criterion of '{imaging.name}', but it has none configured."
            )

    def _run_sweep_and_apply_best(self) -> None:
        """
        Run the configured mode to completion and apply the best value.

        Sweeps again by the same rule as during acquisition (see `_should_sweep_again`).
        """
        try:
            while True:
                self._sweep_base_value = (
                    self._sweeping.get_attribute_value()
                    if self._sweeping is not None
                    else None
                )

                # imaging is only needed for step mode, which is not testable
                for _ in self._mode.execute(self._autofocus_ctx, self._jobs, None):
                    self._jobs.wait()

                results = self._jobs.wait_and_collect()
                sweep_number = self._sweeps_done + 1
                best = self._apply_best_and_log(results)
                edge = self._edge_reached(results, best)
                self._sweeps_done = sweep_number
                if not self._should_sweep_again(edge):
                    return

                self._last_edge = edge
                self._ctx.text_logger.info(
                    f"Best value lies at the {'upper' if edge == 1 else 'lower'} edge of the "
                    f"sweep. Starting sweep {sweep_number + 1} of at most {self._max_sweeps()}."
                )
                self._reset_jobs()
        finally:
            self._end_run()

    def _resolve_imaging(self) -> Imaging:
        imaging = self._actions.named(self._settings.linked_imaging)
        if not isinstance(imaging, Imaging):
            raise AutofocusError(
                f"Linked action is not an Imaging action: {imaging.name}"
            )
        return imaging

    def _advance(self) -> SweepStep | None:
        """
        Advance the active sweep by one step, and start the next sweep if the run continues.

        When a sweep finishes, its best value is applied. If that value lies at
        the edge of the swept range, another sweep centered on it follows:
        basic and line mode complete it right away, step mode returns its first trial value.

        Returns:
            The trial step the next acquisition must use, or `None` if the
            autofocus run finished and its best value was applied.
        """
        assert self._active_gen is not None
        self._current_step_index += 1

        try:
            trial = next(self._active_gen)
            # wait so that the stored state contains every result; otherwise
            # restoring after an interrupt has to deal with half-finished jobs
            self._jobs.wait()
        except StopIteration:
            pass
        except Exception:
            self._abort_sweep()
            raise
        else:
            return trial

        sweep_number = self._sweeps_done + 1
        try:
            results = self._jobs.wait_and_collect()
            best = self._apply_best_and_log(results)
            edge = self._edge_reached(results, best)
        finally:
            # clear even if evaluation fails, so the next slice starts afresh
            self._active_gen = None
            self._current_step_index = 0
            self._sweep_base_value = None

        self._sweeps_done = sweep_number
        if self._should_sweep_again(edge):
            self._last_edge = edge
            self._ctx.text_logger.info(
                f"Best value lies at the {'upper' if edge == 1 else 'lower'} edge of the "
                f"sweep. Starting sweep {sweep_number + 1} of at most {self._max_sweeps()}."
            )
            try:
                self._start_sweep()
            except Exception:
                self._end_run()
                raise
            # basic and line mode complete the new sweep here; step mode
            # returns its first trial value
            return self._advance()

        self._end_run()
        if self._settings.grab_frame_after:
            self._save_result_frame("after_autofocus")

        return None

    def _abort_sweep(self) -> None:
        """Close and discard the active sweep."""
        # TODO: the linked imaging keeps the last trial value until the next sweep
        # this should eventually be fixed, but it breaks the current architecture
        assert self._active_gen is not None
        self._active_gen.close()
        self._active_gen = None
        self._current_step_index = 0
        self._sweep_base_value = None
        self._end_run()

    def _reset_jobs(self) -> None:
        """
        Discard the previous sweep's jobs and resize the pool if `max_workers` changed.

        Called only between sweeps, so a sweep in progress keeps the pool its jobs run on.
        """
        self._jobs.wait_and_clear()
        if self._executor_workers == self._settings.max_workers:
            return

        # every job was waited for, so the old pool is idle
        self._executor.shutdown(wait=False)
        self._executor_workers = self._settings.max_workers
        self._executor = ThreadPoolExecutor(self._executor_workers)
        self._jobs = JobsManager(executor=self._executor)

    def _edge_reached(
        self, results: list[AutofocusResult], best: float | None
    ) -> Literal[-1, 1] | None:
        """
        Return the edge of the swept range the best value lies at.

        Both strategies return one of the swept values, so the edges are found
        by comparison with the lowest and highest values in the results.

        Args:
            results: The finished sweep's results.
            best: The best value applied, or None if nothing was swept (Autoscript).

        Returns:
            1 for the highest swept value, -1 for the lowest, or None if the
            best lies inside the range or equals the base value: nothing moved,
            so sweeping again around it would repeat the same sweep.
        """
        if best is None or not results:
            return None

        if self._sweep_base_value is not None and np.isclose(
            best, self._sweep_base_value
        ):
            return None

        values = [r.sweep.value for r in results]
        if best == max(values):
            return 1
        if best == min(values):
            return -1
        return None

    def _should_sweep_again(self, edge: Literal[-1, 1] | None) -> bool:
        """
        Decide whether the autofocus run continues with another sweep.

        Another sweep follows while the best value keeps hitting the same edge
        of the swept range, i.e. while the optimum probably lies beyond it, and
        `max_sweeps` has not been reached.

        Args:
            edge: The edge the finished sweep's best value lies at, if any.

        Returns:
            True if another sweep should start.
        """
        return (
            edge is not None
            and (self._last_edge is None or edge == self._last_edge)
            and self._sweeps_done < self._max_sweeps()
        )

    def _max_sweeps(self) -> int:
        """
        Return the most sweeps one autofocus run may perform.

        Returns:
            The mode's `max_sweeps`; 1 for the Autoscript modes, which do not sweep.
        """
        match self._settings.mode:
            case BasicModeSettings() | LineModeSettings() | StepModeSettings() as mode:
                return mode.max_sweeps
            case _:
                return 1

    def _end_run(self) -> None:
        """Reset the sweep count and edge, so that the next autofocus run starts afresh."""
        self._sweeps_done = 0
        self._last_edge = None

    def _apply_best_and_log(self, results: list[AutofocusResult]) -> float | None:
        """
        Apply the best sweep value to the microscope and log the focus curve.

        Does nothing if no sweeping is configured (Autoscript mode).

        Args:
            results: Results collected during the sweep.

        Returns:
            The best value applied, or None in Autoscript mode.
        """
        if self._sweeping is None:
            return None

        best = self._sweeping.evaluate_best_sweep(results)
        self._ctx.text_logger.info(f"Best sweep attribute value: {best}.")
        self._sweeping.set_attribute_value(best)

        self._log_af_curve(results, best, self._sweep_base_value)
        if isinstance(self._mode, LineMode):
            self._log_line_focus_image(results)

        return best

    def _log_af_curve(
        self, results: list[AutofocusResult], best: float, base: Any | None
    ) -> None:
        """
        Log the autofocus criterion curve with markers for the base sweep and best value.

        Args:
            results: Autofocus results collected during the sweep.
            best: The sweep value selected as optimal.
        """
        if not results:
            return

        sorted_results = sorted(results, key=lambda r: r.sweep.index)

        # average sharpness per (repetition, sweep value) to handle line mode
        # where multiple results share the same sweep value
        averaged: dict[tuple[int, float], list[float]] = defaultdict(list)
        for r in sorted_results:
            averaged[(r.sweep.repetition, r.sweep.value)].append(r.sharpness)

        repetitions: dict[int, list[tuple[float, float]]] = defaultdict(list)
        for (rep, value), sharpnesses in averaged.items():
            repetitions[rep].append((value, float(np.mean(sharpnesses))))

        _CURVE_COLORS = [
            "#0000FF",
            "#3355DD",
            "#6699BB",
            "#BB6699",
            "#DD5533",
            "#FF0000",
        ]

        # plot the criterion values
        elements: list[PlotElement] = [
            Curve(
                x=[v for v, _ in sorted(rep_points, key=lambda p: p[0])],
                y=[s for _, s in sorted(rep_points, key=lambda p: p[0])],
                color=_CURVE_COLORS[rep % len(_CURVE_COLORS)],
                linewidth=1.0,
            )
            for rep, rep_points in repetitions.items()
        ]

        # mark the base value
        if base is not None:
            elements.append(VerticalLine(x=float(base), color="orange", linewidth=1.0))
        # mark the best value
        elements.append(VerticalLine(x=best, color="green", linewidth=1.0))

        self._ctx.image_logger.save_plot(
            filename="af_curve.png",
            elements=elements,
            title="Focus criterion",
            xlabel=self._settings.target_attribute,
            ylabel="Sharpness",
        )

    def _log_line_focus_image(self, results: list[AutofocusResult]) -> None:
        """
        Log the line focus image with per-line sharpness overlaid as a polyline.

        Args:
            results: Autofocus results collected during the sweep, one per line.
        """
        if not results:
            return

        # the frame the sweep was evaluated on; the line indices refer to it
        if (image := self._autofocus_ctx.line_focus_image) is None:
            self._ctx.text_logger.warning(
                "Line focus image is not available for logging."
            )
            return

        # the sharpness evaluation jobs can be completed in any order
        sorted_results = sorted(results, key=_get_line_index)
        sharpness_values = [r.sharpness for r in sorted_results]
        line_indices = [
            r.sweep.line_index for r in sorted_results if r.sweep.line_index is not None
        ]

        if max(sharpness_values) == 0:
            self._ctx.text_logger.warning(
                "Max sharpness value is 0. Unable to normalize the sharpness, skipping logging."
            )
            return

        # scale for normalizing sharpness to fit the image
        scale = image.shape[1] / max(sharpness_values)

        self._ctx.image_logger.save_image(
            filename=f"{self.name_with_underscores}_line_focus.png",
            img=image,
            overlays=[
                PolylineOverlay(
                    points=[
                        PixelPoint(x=int(v * scale), y=line_idx)
                        for v, line_idx in zip(sharpness_values, line_indices)
                    ],
                    color="red",
                )
            ],
            title="Line focus plot",
        )


def _get_line_index(result: AutofocusResult) -> int:
    """Extract global index of the line in the image that this result corresponds to."""
    assert result.sweep.line_index is not None

    return result.sweep.line_index
