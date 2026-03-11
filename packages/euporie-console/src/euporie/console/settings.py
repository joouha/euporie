"""Console app settings definitions."""

from __future__ import annotations

from upath import UPath

from euporie.core.config._setting import Setting

mouse_support = Setting(
    name="mouse_support",
    flags=["--mouse-support"],
    type_=bool,
    help_="Enable or disable mouse support",
    default=None,
    description="""
        When set to True, mouse support is enabled. When set to False, mouse
        support is disabled.
    """,
)

max_stored_outputs = Setting(
    name="max_stored_outputs",
    flags=["--max-stored-outputs"],
    type_=int,
    help_="The number of inputs / outputs to store in an in-memory notebook",
    default=100,
    schema={
        "minimum": 0,
    },
    description="""
        Defines the maximum number of executed "cells" to store in case the console
        session is saved to a file or converted into a notebook.
    """,
)

connection_file = Setting(
    name="connection_file",
    flags=["--connection-file", "--kernel-connection-file"],
    type_=UPath,
    help_="Attempt to connect to an existing kernel using a JSON connection info file",
    default=None,
    description="""
        If the file does not exist, kernel connection information will be written
        to the file path provided.

        If the file exists, kernel connection info will be read from the file,
        allowing euporie to connect to existing kernels.
    """,
)
