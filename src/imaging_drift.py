# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import argparse
import logging
from pathlib import Path

from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.scanning_area import RelativeScanningArea
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.drift_correction.template_matching import (
    TemplateMatchingDriftCorrection,
)
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.context import LogContext, SliceContext
from fibsem_maestro.logging.image.slice_aware import SliceAwareImageLogger
from fibsem_maestro.logging.text.slice_aware import SliceAwareTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings


def main():
    parser = argparse.ArgumentParser(description="Control the imaging.")

    # define arguments
    parser.add_argument(
        "--microscope",
        type=Path,
        required=True,
        help="Path to the YAML file containing microscope settings.",
    )
    parser.add_argument(
        "--imaging",
        type=Path,
        required=True,
        help="Path to the YAML file containing imaging settings.",
    )
    parser.add_argument(
        "--drift",
        type=Path,
        required=True,
        help="Path to the YAML file containing drift correction settings.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs"),
        help="Directory to store log files. Defaults to 'logs'.",
    )
    parser.add_argument(
        "--slices",
        type=int,
        default=1,
        help="Number of imagings to perform.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level).",
    )

    # parse the arguments
    args = parser.parse_args()

    # load settings
    microscope_settings = MicroscopeSettings.from_file(args.microscope)
    imaging_settings = ImagingSettings.from_file(args.imaging)
    drift_corr_settings = TemplateMatchingSettings.from_file(args.drift)

    # initialize the logging
    slice = SliceContext(1)
    log_context = LogContext(Path(args.log_dir), slice, logging.DEBUG)
    txt_log = SliceAwareTextLogger("microscope", log_context)
    img_log = SliceAwareImageLogger(log_context)

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log, img_log)

    # initialize the imaging
    imaging = Imaging(
        microscope,
        imaging_settings,
        log_ctx=log_context,
        txt_log=txt_log.derive("imaging"),
    )

    # initialize the drift correction
    drift_correction = TemplateMatchingDriftCorrection(
        microscope,
        drift_corr_settings,
        imaging,
        log_context,
        txt_log.derive("template matching"),
        img_log,
    )

    # set microscope properties manually
    # input("Set microscope properties interactively and then press ENTER.")

    microscope._control.try_set_stage_position(
        StagePosition(x=10_000.0, y=10_000.0, z=5_000_000.0, rotation=0, tilt=0)
    )
    microscope.beam.resolution = Resolution(1024, 768)
    microscope.beam.horizontal_field_width = 2000
    # microscope.beam.line_integration = 12

    # save microscope properties
    imaging.save_properties()
    drift_correction.save_properties()
    # create templates for drift correction
    drift_correction.create_templates()

    # optionally change microscope properties to test that the previously saved properties are reloaded before imaging
    # input("Microscope properties saved. Press ENTER.")

    # run imaging
    for _ in range(args.slices):
        drift_correction.correct_drift()
        imaging.grab_frame()
        slice.increment()


if __name__ == "__main__":
    main()
