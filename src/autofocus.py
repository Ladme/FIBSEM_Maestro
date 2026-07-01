# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import argparse
import logging
import random
from pathlib import Path

from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.autofocus.autofocus import Autofocus
from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.drift_correction.drift_correction import DriftCorrection
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.microscope.simulated.microscope_control import (
    SimulatedMicroscopeControl,
)
from fibsem_maestro.settings.autofocus_settings import AutofocusSettings
from fibsem_maestro.settings.drift_correction_settings import DriftCorrectionSettings
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow


def main():
    parser = argparse.ArgumentParser(description="Control imaging with autofocus.")

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
        "--autofunction",
        type=Path,
        required=True,
        help="Path to the YAML file containing autofunction settings.",
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
        autofocus_settings = AutofocusSettings.from_file(args.autofunction)
        drift_corr_settings = DriftCorrectionSettings.from_file(args.drift)

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

        # initialize the drift correction
        drift_correction = DriftCorrection(
            "drift correction",
            microscope,
            drift_corr_settings,
            FileActionContext(
                args.log_dir / "drift_correction",
                "drift_correction",
                log_level=logging.DEBUG if args.verbose else logging.INFO,
            ),
            actions,
        )
        actions.append(drift_correction)

        # initialize autofocus
        autofocus = Autofocus(
            "autofocus",
            microscope,
            autofocus_settings,
            FileActionContext(
                args.log_dir / "autofocus",
                "autofocus",
                log_level=logging.DEBUG if args.verbose else logging.INFO,
            ),
            actions,
        )
        actions.append(autofocus)

        # initialize the imaging
        imaging = Imaging(
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
        actions.append(imaging)

        microscope._control.try_set_stage_position(
            StagePosition(x=0.0, y=0.0, z=5_000_000.0, rotation=0, tilt=0)
        )
        microscope.beam.resolution = Resolution(2048, 1536)
        microscope.beam.horizontal_field_width = 2000

        drift_correction.collect_and_write_properties(
            drift_correction.ctx.props_store.next
        )
        drift_correction.setup(drift_correction.ctx.image_store(Image8Bit).next)

        microscope.beam.line_integration = 5
        autofocus.collect_and_write_properties(autofocus.ctx.props_store.next)

        microscope.beam.resolution = Resolution(1024, 768)
        microscope.beam.line_integration = 1

        imaging.collect_and_write_properties(imaging.ctx.props_store.next)

        propagations = Propagations(workflow_ctx.text_logger.derive("propagations"))
        propagations.register_rule(
            drift_correction.name,
            [autofocus.name, imaging.name],
            PropertyNames(microscope=["stage_position"], electron_beam=["beam_shift"]),
        )
        propagations.register_rule(
            autofocus.name,
            [drift_correction.name, imaging.name],
            PropertyNames(electron_beam=["working_distance"]),
        )

        workflow = Workflow(microscope, actions, propagations, workflow_ctx)

        workflow.run(0)
    else:
        workflow = Workflow.import_from_dir_with_state(args.resume)
        microscope = workflow.microscope
        # set correct drift
        drift = (58.0, -16.0, 176.0)
        if isinstance(microscope.control, SimulatedMicroscopeControl):
            microscope.control._sample.apply_drift(
                drift_x=drift[0], drift_y=drift[1], drift_z=drift[2]
            )

    for _ in range(args.slices):
        control = microscope._control
        if isinstance(control, SimulatedMicroscopeControl):
            control._sample.apply_drift(  # pyright: ignore[reportAttributeAccessIssue]
                drift_x=random.randrange(-40, 41),
                drift_y=random.randrange(-40, 41),
                # drift_z=random.choice([-10_000, -5000, 0, 5000, 10_000]),
                # drift_x=-10,
                # drift_y=-10,
                # drift_z=1_000,
                drift_z=random.randrange(-2000, 2001),
                # drift_z=10_000,
            )
            print(control._sample.drift)  # pyright: ignore[reportAttributeAccessIssue]
        workflow._run_slice()


if __name__ == "__main__":
    main()
