# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import argparse
import logging
from pathlib import Path

from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow


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
    parser.add_argument(
        "-r",
        "--resume",
        type=Path,
        default=None,
        help="Directory containing the workflow to resume.",
    )

    # parse the arguments
    args = parser.parse_args()

    if args.resume is None:
        # load settings
        microscope_settings = MicroscopeSettings.from_file(args.microscope)
        imaging_settings = ImagingSettings.from_file(args.imaging)

        # initialize the main workflow context
        workflow_ctx = FileActionContext(
            args.log_dir / "workflow",
            "workflow",
            log_level=logging.DEBUG if args.verbose else logging.INFO,
        )

        # initialize the microscope
        microscope = Microscope(
            microscope_settings,
            ContextualTextLogger(fallback=workflow_ctx.text_logger).derive(
                "microscope"
            ),
        )

        actions = Actions()

        # initialize the imaging
        actions.append(
            Imaging(
                "imaging",
                microscope,
                imaging_settings,
                FileActionContext(
                    args.log_dir / "imaging",
                    "imaging",
                    log_level=logging.DEBUG if args.verbose else logging.INFO,
                ),
                actions,
            )
        )

        imaging = actions[0]

        # set microscope properties manually
        input("Set microscope properties interactively and then press ENTER.")

        microscope._control.try_set_stage_position(
            StagePosition(x=0.0, y=0.0, z=5_000_000.0, rotation=0, tilt=0)
        )
        microscope.beam.resolution = Resolution(1000, 1000)
        microscope.beam.horizontal_field_width = 2000
        # microscope.beam.scanning_area = RelativeArea(
        #    origin=RelativePoint(x=0.25, y=0.5), width=0.5, height=0.25
        # )

        # save microscope properties
        imaging.collect_and_write_properties(imaging.ctx.props_store.next)

        # optionally change microscope properties to test that the previously saved properties are reloaded before imaging
        input("Microscope properties saved. Press ENTER.")

        # prepare the workflow
        workflow = Workflow(
            microscope,
            actions,
            Propagations(workflow_ctx.text_logger.derive("propagations")),
            workflow_ctx,
        )
    else:
        workflow = Workflow.import_from_dir_with_state(args.resume)

    workflow.run(args.slices)


if __name__ == "__main__":
    main()
