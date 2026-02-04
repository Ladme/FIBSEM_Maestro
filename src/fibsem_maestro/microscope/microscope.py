# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import fields

from scipy.spatial import distance  # pyright: ignore[reportMissingTypeStubs]

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope_registry import MicroscopeRegistry
from fibsem_maestro.settings.global_properties import GlobalProperties
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.property_names import PropertyNames


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
            self._settings.ip_address, self._txt_log
        )
        self.beam = self._control.electron_beam

    def _update(self, settings: MicroscopeSettings) -> None:
        self._apply_settings(settings)

    def export_imaging_settings(self) -> ImagingSettings:
        values = {f.name: getattr(self, f.name) for f in fields(ImagingSettings)}
        return ImagingSettings(**values)

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
        # try setting beam shift
        self.beam.beam_shift = new_beam_shift
        actual_beam_shift = self.beam.beam_shift

        dist = distance.euclidean(
            actual_beam_shift.to_tuple(), new_beam_shift.to_tuple()
        )

        if dist > self._settings.beam_shift_tolerance:
            self._txt_log.warning(
                f"Beam shift out of range: "
                f"target={new_beam_shift}, actual={actual_beam_shift}, dist={dist:.3f} > tol={self._settings.beam_shift_tolerance}"
            )

            rel_shift_to_stage = self._settings.relative_beam_shift_to_stage
            # TODO: handle this properly
            assert self.beam.beam_shift_to_stage_move is not None

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
            self.beam.beam_shift = BeamShift(0.0, 0.0)

    def set_properties(
        self, properties: GlobalProperties, beam: BeamType | None
    ) -> None:
        self._control.set_properties(properties, beam)

    def collect_properties(
        self, properties_to_collect: PropertyNames
    ) -> GlobalProperties:
        return self._control.collect_properties(properties_to_collect)

    def get_property_names(self) -> PropertyNames:
        return self._control.prop_names
