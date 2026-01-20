# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import argparse
import logging
from pathlib import Path

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.logging.context import LogContext, SliceContext
from fibsem_maestro.logging.image.slice_aware import SliceAwareImageLogger
from fibsem_maestro.logging.text.central import CentralTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_properties import MicroscopeProperties
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


def main():
    parser = argparse.ArgumentParser(
        description="Configure and control the microscope."
    )

    # define arguments
    parser.add_argument(
        "--settings",
        type=Path,
        required=True,
        help="Path to the microscope settings YAML file.",
    )
    parser.add_argument(
        "--params",
        type=Path,
        required=True,
        help="Path to the microscope parameters YAML file.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs"),
        help="Directory to store log files. Defaults to 'logs'.",
    )
    parser.add_argument(
        "--log-level",
        type=int,
        default=logging.INFO,
        choices=[
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ],
        help="Log level. Defaults to INFO.",
    )

    beam_group = parser.add_mutually_exclusive_group()
    beam_group.add_argument(
        "-e",
        "--electron",
        action="store_true",
        help="Use electron beam properties.",
    )
    beam_group.add_argument(
        "-i",
        "--ion",
        action="store_true",
        help="Use ion beam properties.",
    )

    # parse the arguments
    args = parser.parse_args()

    # load settings and properties from files
    microscope_settings = MicroscopeSettings.from_file(args.settings)
    microscope_params = MicroscopeProperties.from_file(args.params)

    # set up logging
    log_context = LogContext(args.log_dir, SliceContext(None), args.log_level)
    txt_log = CentralTextLogger("microscope", log_context)
    img_log = SliceAwareImageLogger(log_context)

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log, img_log)

    # determine beam type based on arguments
    beam_type = None
    if args.electron and args.ion:
        beam_type = None  # set all properties
    elif args.electron:
        beam_type = BeamType.ELECTRON
    elif args.ion:
        beam_type = BeamType.ION

    # set microscope properties
    microscope.set_properties(microscope_params, beam_type)


if __name__ == "__main__":
    main()
