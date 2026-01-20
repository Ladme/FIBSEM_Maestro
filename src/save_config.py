# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import argparse
import logging
from pathlib import Path

from fibsem_maestro.logging.context import LogContext, SliceContext
from fibsem_maestro.logging.image.slice_aware import SliceAwareImageLogger
from fibsem_maestro.logging.text.central import CentralTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


def main():
    parser = argparse.ArgumentParser(
        description="Collect and export selected parameters of the microscope."
    )

    # define arguments
    parser.add_argument(
        "--settings",
        type=Path,
        required=True,
        help="Path to the settings YAML file.",
    )
    parser.add_argument(
        "--params",
        type=Path,
        required=True,
        help="Path to an output YAML file where collected microscope parameters will be written to.",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("logs"),
        help="Directory to store log files. Defaults to 'logs'.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level).",
    )

    # parse the arguments
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO

    # load settings
    microscope_settings = MicroscopeSettings.from_file(args.settings)

    # set up logging
    log_context = LogContext(args.log_dir, SliceContext(None), log_level)
    txt_log = CentralTextLogger("microscope", log_context)
    img_log = SliceAwareImageLogger(log_context)  # noqa: F821

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log, img_log)

    # collect the parameters of the microscope
    microscope_params = microscope.collect_properties()

    microscope_params.to_file(args.params)


if __name__ == "__main__":
    main()
