# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import argparse
import logging
from pathlib import Path

from fibsem_maestro.action.action import Action, ActionConfig
from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.file import FileImageLogger
from fibsem_maestro.logging.text.file import FileTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.milling.milling import Milling
from fibsem_maestro.post_milling_correction.correction import (
    LinkedToPostMillingCorrection,
    PostMillingCorrection,
)
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.milling_settings import MillingSettings
from fibsem_maestro.settings.post_milling_correction_settings import (
    PostMillingCorrectionSettings,
)
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.frame.file import FileFrameStore
from fibsem_maestro.store.image.file import FileImageStore
from fibsem_maestro.store.props.file import FilePropsStore
from fibsem_maestro.store.text.file import FileTextStore
from fibsem_maestro.workflow.links import ActionLinks
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow


def main():
    parser = argparse.ArgumentParser(
        description="Control the milling and post-milling correction."
    )

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
        "--correction",
        type=Path,
        required=True,
        help="Path to the YAML file containing post-milling correction settings.",
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
    post_milling_corr_settings = PostMillingCorrectionSettings.from_file(
        args.correction
    )
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
    image_store = FileImageStore(slice, Image8Bit, directory=Path("stored_images"))

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log)

    # initialize the imaging
    imaging_config = ActionConfig[ImagingSettings](
        name="imaging",
        microscope=microscope,
        settings=imaging_settings,
        props_store=props_store,
        frame_store=frame_store,
        txt_store=txt_store,
        image_store=image_store,
        txt_log=txt_log.derive("imaging"),
        img_log=img_log,
    )
    imaging = Imaging(imaging_config)

    # initialize the milling
    milling_config = ActionConfig[MillingSettings](
        name="milling",
        microscope=microscope,
        settings=milling_settings,
        props_store=props_store,
        frame_store=frame_store,
        txt_store=txt_store,
        image_store=image_store,
        txt_log=txt_log.derive("milling"),
        img_log=img_log,
    )
    milling = Milling(milling_config)

    # initialize the post-milling correction
    corr_config = ActionConfig[PostMillingCorrectionSettings](
        name="post milling correction",
        microscope=microscope,
        settings=post_milling_corr_settings,
        props_store=props_store,
        frame_store=frame_store,
        txt_store=txt_store,
        image_store=image_store,
        txt_log=txt_log.derive("post_milling_correction"),
        img_log=img_log,
    )
    post_milling_correction = PostMillingCorrection(corr_config)

    # set microscope properties manually
    # input("Set microscope properties for imaging interactively and then press ENTER.")

    microscope._control.try_set_stage_position(
        StagePosition(x=0.0, y=0.0, z=5_000_000.0, rotation=0, tilt=0)
    )
    microscope.beam.resolution = Resolution(1024, 768)
    microscope.beam.horizontal_field_width = 2000

    imaging.collect_and_write_properties(imaging.props_store.next)
    post_milling_correction.collect_and_write_properties(
        post_milling_correction.props_store.next
    )

    # input("Set microscope properties for milling interactively and then press ENTER.")
    milling.collect_and_write_properties(milling.props_store.next)

    # save microscope properties

    # create templates for drift correction
    # drift_correction.setup()

    # optionally change microscope properties to test that the previously saved properties are reloaded before imaging
    # input("Microscope properties saved. Press ENTER.")

    propagations = Propagations(txt_log.derive("propagations"))
    propagations.register_rule(
        "post milling correction",
        ["imaging"],
        PropertyNames(
            electron_beam=["working_distance", "beam_shift"],
            microscope=["stage_position"],
        ),
    )

    links = ActionLinks(txt_log.derive("links"))
    links.register_rule(
        "post milling correction",
        LinkedToPostMillingCorrection(
            milling=milling,
        ),
    )

    actions: list[Action] = [milling, post_milling_correction, imaging]
    workflow = Workflow(
        slice,
        actions,
        propagations,
        links,
        txt_log.derive("workflow"),
    )

    workflow.run(args.slices)


if __name__ == "__main__":
    main()
