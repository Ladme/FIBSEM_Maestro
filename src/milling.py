# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import argparse
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.file import FileImageLogger
from fibsem_maestro.logging.text.file import FileTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.milling.milling import Milling
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.milling_settings import MillingSettings
from fibsem_maestro.store.frame.file import FileFrameStore
from fibsem_maestro.store.props.file import FilePropsStore
from fibsem_maestro.store.text.file import FileTextStore
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow

if TYPE_CHECKING:
    from fibsem_maestro.core.action import Action


def main():
    parser = argparse.ArgumentParser(description="Control the milling.")

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
        "--milling",
        type=Path,
        required=True,
        help="Path to the YAML file containing milling settings.",
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
    # drift_corr_settings = DriftCorrectionSettings.from_file(args.drift)
    milling_settings = MillingSettings.from_file(args.milling)

    # initialize the loggers and stores
    slice = SliceContext(Path("logs"), 0)
    txt_log = FileTextLogger(
        slice, "microscope", logging.DEBUG if args.verbose else logging.INFO
    )
    img_log = FileImageLogger(slice)
    props_store = FilePropsStore(slice)
    frame_store = FileFrameStore(slice, imaging_settings.images_directory)
    txt_store = FileTextStore(slice)
    # image_store = FileImageStore(slice, Image8Bit, Path("templates"))

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log)

    # initialize the imaging
    imaging = Imaging(
        "imaging",
        microscope,
        imaging_settings,
        props_store,
        frame_store,
        txt_log.derive("imaging"),
        img_log,
    )

    # initialize the milling
    milling = Milling(
        "milling", microscope, milling_settings, props_store, txt_store, txt_log
    )

    # set microscope properties manually
    # input("Set microscope properties for imaging interactively and then press ENTER.")

    microscope._control.try_set_stage_position(
        StagePosition(x=0.0, y=0.0, z=5_000_000.0, rotation=0, tilt=0)
    )
    microscope.beam.resolution = Resolution(1024, 768)
    microscope.beam.horizontal_field_width = 2000

    imaging.collect_and_write_properties(imaging.props_store.next)

    # input("Set microscope properties for milling interactively and then press ENTER.")
    milling.collect_and_write_properties(milling.props_store.next)

    # save microscope properties

    # create templates for drift correction
    # drift_correction.setup()

    # optionally change microscope properties to test that the previously saved properties are reloaded before imaging
    # input("Microscope properties saved. Press ENTER.")

    actions: list[Action] = [milling, imaging]
    workflow = Workflow(
        slice,
        actions,
        Propagations(actions, txt_log.derive("propagations")),
        txt_log.derive("workflow"),
    )

    workflow.run(args.slices)


if __name__ == "__main__":
    main()
