# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import fields

from scipy.spatial import distance  # pyright: ignore[reportMissingTypeStubs]

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.core.scanning_area import ScanningArea
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope_registry import MicroscopeRegistry
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


class Microscope:
    def __init__(
        self,
        settings: MicroscopeSettings,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._txt_log = txt_log
        self._img_log = img_log

        self._apply_settings(settings)
        self._settings.on_change(self._update)

    def _apply_settings(self, settings: MicroscopeSettings) -> None:
        self._settings = settings
        self._control = MicroscopeRegistry.get(settings.control)(
            self._settings.ip_address
        )
        self.beam = self._control.electron_beam

    def _update(self, settings: MicroscopeSettings) -> None:
        self._apply_settings(settings)

    def set_imaging_settings(self, settings: ImagingSettings) -> None:
        if settings.bit_depth is not None:
            self.beam.bit_depth = settings.bit_depth

        if settings.field_of_view is not None:
            self.beam.horizontal_field_width = settings.field_of_view[0]
            self.beam.vertical_field_width = settings.field_of_view[1]

        if settings.pixel_size is not None:
            self.beam.resolution = (
                int(self.beam.horizontal_field_width / settings.pixel_size),
                int(self.beam.vertical_field_width / settings.pixel_size),
            )

        if settings.resolution is not None:
            self.beam.resolution = settings.resolution

        if settings.line_integration is not None:
            self.beam.line_integration = settings.line_integration

        if settings.dwell_time is not None:
            self.beam.dwell_time = settings.dwell_time

        if settings.detector_contrast is not None:
            self.beam.detector_contrast = settings.detector_contrast

        if settings.detector_brightness is not None:
            self.beam.detector_brightness = settings.detector_brightness

        if settings.scanning_area is not None:
            self.beam.scanning_area = settings.scanning_area

    def export_imaging_settings(self) -> ImagingSettings:
        values = {f.name: getattr(self, f.name) for f in fields(ImagingSettings)}
        return ImagingSettings(**values)

    @contextmanager
    def temporary_imaging_settings(
        self,
        settings: ImagingSettings,
    ) -> Iterator[None]:
        """
        Temporarily apply imaging settings and restore the previous ones on exit.
        """
        backup = self.export_imaging_settings()

        try:
            self.set_imaging_settings(settings)
            yield
        finally:
            self.set_imaging_settings(backup)

    @contextmanager
    def total_blank(self) -> Iterator[None]:
        """
        Temporarily blank the beam with zero detector contrast and brightness.
        """
        blank_settings = ImagingSettings(
            detector_contrast=0,
            detector_brightness=0,
        )

        with self.temporary_imaging_settings(blank_settings):
            self.beam.blank()
            try:
                yield
            finally:
                self.beam.unblank()

    def set_stage_position_with_verification(
        self, new_stage_position: StagePosition
    ) -> None:
        for attempt in range(1, self._settings.stage_trials + 1):
            # set position
            actual_position = self._control.try_set_stage_position(new_stage_position)

            # check whether the movement is within tolerance
            dist = distance.euclidean(
                actual_position.to_xy(), new_stage_position.to_xy()
            )

            if dist <= self._settings.stage_tolerance:
                # success
                return

            self._txt_log.warning(
                f"Stage off target (attempt {attempt}/{self._settings.stage_trials}): "
                f"target={new_stage_position}, actual={actual_position}, dist={dist:.3f} > tol={self._settings.stage_tolerance}"
            )

    def set_beam_shift_with_verification(self, new_beam_shift: BeamShift) -> None:
        actual_beam_shift = self.beam.try_set_beam_shift(new_beam_shift)

        dist = distance.euclidean(
            actual_beam_shift.to_tuple(), new_beam_shift.to_tuple()
        )

        if dist > self._settings.beam_shift_tolerance:
            self._txt_log.warning(
                f"Beam shift out of range: "
                f"target={new_beam_shift}, actual={actual_beam_shift}, dist={dist:.3f} > tol={self._settings.beam_shift_tolerance}"
            )

            rel_shift_to_stage = self._settings.relative_beam_shift_to_stage
            new_stage_move = (
                new_beam_shift.x
                * rel_shift_to_stage[0]
                * self.beam.beam_shift_to_stage_move[0],
                new_beam_shift.y
                * rel_shift_to_stage[1]
                * self.beam.beam_shift_to_stage_move[1],
            )

            # move stage
            self._control.try_move_stage_position(
                StagePosition(x=new_stage_move[0], y=new_stage_move[1])
            )
            # set beam shift to zero
            self.beam.try_set_beam_shift(BeamShift(0.0, 0.0))

    def blank_screen(self):
        with self.temporary_imaging_settings(
            ImagingSettings(
                pixel_size=20,
                line_integration=1,
                scanning_area=ScanningArea(
                    origin=RelativePoint(0, 0), width=0.0, height=0.0
                ),
                detector_contrast=0.0,
                detector_brightness=0.0,
            )
        ):
            self.beam.blank()
            self.beam.grab_frame()
