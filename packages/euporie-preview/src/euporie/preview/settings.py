"""Preview app settings definitions."""

from __future__ import annotations

from upath import UPath

from euporie.core.config._setting import Setting

output_file = Setting(
    name="output_file",
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

page = Setting(
    name="page",
    flags=["--page"],
    type_=bool,
    help_="Pass output to pager",
    default=False,
    description="""
        Whether to pipe output to the system pager when previewing a notebook.
    """,
)

run = Setting(
    name="run",
    flags=["--run"],
    type_=bool,
    help_="Run the notebook files when loaded",
    default=False,
    description="""
        If set, notebooks will be run automatically when opened, or if previewing a
        file, the notebooks will be run before being output.
    """,
)

save = Setting(
    name="save",
    flags=["--save"],
    type_=bool,
    help_="Save the notebook after running it",
    default=False,
    description="""
        If set, notebooks will be saved after they have been run. This setting only
        has any affect if the :option:`run` setting is active.
    """,
)

show_filenames = Setting(
    name="show_filenames",
    flags=["--show-filenames"],
    type_=bool,
    help_="Show the notebook filenames when previewing multiple notebooks",
    default=False,
    description="""
        If set, the notebook filenames will be printed above each notebook's output
        when multiple notebooks are being previewed.
    """,
)

cell_start = Setting(
    name="cell_start",
    flags=["--cell-start"],
    type_=int,
    help_="The first cell to include in the preview",
    default=None,
    description="""
        When set, only cells after the given cell index will be shown.
    """,
)

cell_stop = Setting(
    name="cell_stop",
    flags=["--cell-stop"],
    type_=int,
    help_="The last cell to include in the preview",
    default=None,
    description="""
        When set, only cells before the given cell index will be shown.
    """,
)
