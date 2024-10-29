"""Define settings for the preview app."""

from __future__ import annotations

import logging

from upath import UPath

from euporie.core.config import add_setting

log = logging.getLogger(__name__)


add_setting(
    name="output_file",
    group="euporie.preview.app",
    flags=["--output-file"],
    nargs="?",
    default="-",
    const="-",
    type_=UPath,
    help_="Output path when previewing file",
    description="""
        When set to a file path, the formatted output will be written to the
        given path. If no value is given (or the default "-" is passed) output
        will be printed to standard output.
    """,
)

add_setting(
    name="page",
    group="euporie.preview.app",
    flags=["--page"],
    type_=bool,
    help_="Pass output to pager",
    default=False,
    description="""
        Whether to pipe output to the system pager when previewing a notebook.
    """,
)


add_setting(
    name="run",
    group="euporie.preview.app",
    flags=["--run"],
    type_=bool,
    help_="Run the notebook files when loaded",
    default=False,
    description="""
        If set, notebooks will be run automatically when opened, or if previewing a
        file, the notebooks will be run before being output.
    """,
)

add_setting(
    name="save",
    group="euporie.preview.app",
    flags=["--save"],
    type_=bool,
    help_="Save the notebook after running it",
    default=False,
    description="""
        If set, notebooks will be saved after they have been run. This setting only
        has any affect if the :option:`run` setting is active.
    """,
)

add_setting(
    name="show_filenames",
    group="euporie.preview.app",
    flags=["--show-filenames"],
    type_=bool,
    help_="Show the notebook filenames when previewing multiple notebooks",
    default=False,
    description="""
        If set, the notebook filenames will be printed above each notebook's output
        when multiple notebooks are being previewed.
    """,
)

add_setting(
    name="cell_start",
    group="euporie.preview.app",
    flags=["--cell-start"],
    type_=int,
    help_="The first cell to include in the preview",
    default=None,
    description="""
        When set, only cells after the given cell index will be shown.
    """,
)

add_setting(
    name="cell_stop",
    group="euporie.preview.app",
    flags=["--cell-stop"],
    type_=int,
    help_="The last cell to include in the preview",
    default=None,
    description="""
        When set, only cells before the given cell index will be shown.
    """,
)
