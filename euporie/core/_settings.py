"""Defines core settings."""

import json

from euporie.core import __version__
from euporie.core.config import add_setting

# euporie.core.config

add_setting(
    name="version",
    group="euporie.core.config",
    default=False,
    flags=["--version", "-V"],
    action="version",
    hidden=True,
    version=f"%(prog)s {__version__}",
    help_="Show the version number and exit",
    description="""
        If set, euporie will print the current version number of the application and exit.
        All other configuration options will be ignored.

        .. note::

           This cannot be set in the configuration file or via an environment variable
    """,
)

# euporie.core.log

add_setting(
    name="log_file",
    group="euporie.core.log",
    flags=["--log-file"],
    nargs="?",
    default="",
    type_=str,
    title="the log file path",
    help_="File path for logs",
    description="""
        When set to a file path, the log output will be written to the given path.
        If no value is given output will be sent to the standard output.
    """,
)

add_setting(
    name="log_level",
    group="euporie.core.log",
    type_=str,
    default="warning",
    title="the log level",
    help_="Set the log level",
    choices=["debug", "info", "warning", "error", "critical"],
    description="""
        When set, logging events at the given level are emitted.
    """,
)


add_setting(
    name="log_level_stdout",
    group="euporie.core.log",
    hidden=True,
    type_=str,
    default="critical",
    title="the log level at which to log to standard output",
    help_="Set the log level printed to standard out",
    choices=["debug", "info", "warning", "error", "critical"],
    description="""
        When set, logging events at the given level are printed to the standard output.
    """,
)

add_setting(
    name="log_config",
    group="euporie.core.log",
    flags=["--log-config"],
    type_=json.loads,
    default={},
    schema={
        "type": "object",
    },
    title="additional logging configuration",
    help_="Additional logging configuration",
    description="""
        A JSON string specifying additional logging configuration.
    """,
)

# euporie.core.clipboard

add_setting(
    name="clipboard",
    group="euporie.core.clipboard",
    flags=["--clipboard"],
    choices=["external", "internal", "terminal"],
    type_=str,
    default="external",
    help_="The preferred clipboard access method",
    description="""
        The clipboard access method to use.
        - ``external``: Data is saved to the system clipboard using OS native tooling.
        - ``internal``: Clipboard data is only stored and usable inside euporie - it is
            not saved to the system clipboard.
        - ``terminal``: uses OSC52 escape sequences to retrieve and set the clipboard
            contents. Requires your terminal emulator to support OSC52. Works over SSH.

    """,
)
