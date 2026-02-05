# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import argparse
import logging
from pathlib import Path

from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.scanning_area import RelativeScanningArea
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.context import LogContext, SliceContext
from fibsem_maestro.logging.image.slice_aware import SliceAwareImageLogger
from fibsem_maestro.logging.text.central import CentralTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


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
        "--log-dir",
        type=Path,
        default=Path("logs"),
        help="Directory to store log files. Defaults to 'logs'.",
    )
    parser.add_argument(
        "--img-dir",
        type=Path,
        default=Path("images"),
        help="Directory to store acquired images. Defaults to 'images'.",
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

    microscope_settings = MicroscopeSettings.from_file(args.microscope)
    imaging_settings = ImagingSettings.from_file(args.imaging)

    slice = SliceContext(0)
    log_context = LogContext(Path(args.log_dir), slice, logging.DEBUG)
    txt_log = CentralTextLogger("microscope", log_context)
    img_log = SliceAwareImageLogger(log_context)

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log, img_log)

    # initialize the imaging
    imaging = Imaging(microscope, imaging_settings, slice, txt_log=txt_log)

    # set microscope parameters manually
    # input("Set microscope parameters interactively and then press ENTER.")
    microscope._control.try_set_stage_position(
        StagePosition(x=10_000.0, y=10_000.0, z=5_000_000.0, rotation=0, tilt=0)
    )
    microscope.beam.resolution = Resolution(1000, 1000)
    microscope.beam.horizontal_field_width = 2000
    microscope.beam.scanning_area = RelativeScanningArea(
        RelativePoint(x=0.25, y=0.5), 0.5, 0.25
    )

    # save microscope properties
    imaging.save_properties()

    # run imaging
    for _ in range(args.slices):
        slice.increment()
        imaging.grab_frame()


if __name__ == "__main__":
    main()
