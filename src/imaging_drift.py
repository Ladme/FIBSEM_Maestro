# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import argparse
import logging
import random
from pathlib import Path

from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.drift_correction.template_matching import (
    TemplateMatchingDriftCorrection,
)
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.file import FileImageLogger
from fibsem_maestro.logging.text.file import FileTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.microscope.simulated.microscope_control import (
    SimulatedMicroscopeControl,
)
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings
from fibsem_maestro.store.frame.file import FileFrameStore
from fibsem_maestro.store.image.file import FileImageStore
from fibsem_maestro.store.props.file import FilePropsStore


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

    # initialize the loggers and stores
    slice = SliceContext(Path("logs"), 1)
    txt_log = FileTextLogger(
        slice, "microscope", logging.DEBUG if args.verbose else logging.INFO
    )
    img_log = FileImageLogger(slice)
    props_store = FilePropsStore(slice)
    frame_store = FileFrameStore(slice, imaging_settings.images_directory)
    image_store = FileImageStore(slice, Image8Bit, Path("templates"))

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log)

    # initialize the imaging
    imaging = Imaging(
        microscope,
        imaging_settings,
        props_store,
        frame_store,
        txt_log.derive("imaging"),
    )

    # initialize the drift correction
    drift_correction = TemplateMatchingDriftCorrection(
        microscope,
        drift_corr_settings,
        imaging,
        props_store,
        image_store,
        txt_log.derive("template_matching"),
        img_log,
    )

    # set microscope properties manually
    # input("Set microscope properties interactively and then press ENTER.")

    microscope._control.try_set_stage_position(
        StagePosition(x=0.0, y=0.0, z=5_000_000.0, rotation=0, tilt=0)
    )
    microscope.beam.resolution = Resolution(1024, 768)
    microscope.beam.horizontal_field_width = 2000

    # save microscope properties
    imaging.save_properties()
    drift_correction.save_properties()
    # create templates for drift correction
    drift_correction.create_templates()

    # optionally change microscope properties to test that the previously saved properties are reloaded before imaging
    input("Microscope properties saved. Press ENTER.")

    # run imaging
    for _ in range(args.slices):
        control = microscope._control
        if isinstance(control, SimulatedMicroscopeControl):
            control._sample.apply_drift(  # pyright: ignore[reportAttributeAccessIssue]
                drift_x=random.randrange(-40, 41),
                drift_y=random.randrange(-40, 41),
                # drift_x=-10,
                # drift_y=-10,
            )
            print(control._sample.drift)  # pyright: ignore[reportAttributeAccessIssue]
        drift_correction.correct_drift()
        imaging.grab_frame()
        slice.increment()


if __name__ == "__main__":
    main()
