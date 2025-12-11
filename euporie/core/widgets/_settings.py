"""Defines widget settings."""

from prompt_toolkit.filters import buffer_has_focus

from euporie.core.app.current import get_app
from euporie.core.config import add_setting
from euporie.core.filters import tab_type_has_focus

# euporie.core.widgets.cell_outputs:CellOutputArea

add_setting(
    name="wrap_cell_outputs",
    group="euporie.core.widgets.cell_outputs",
    title="wrap cell outputs",
    flags=["--wrap-cell-outputs"],
    type_=bool,
    help_="Wrap cell output text.",
    default=True,
    schema={"type": "boolean"},
    description="""
        Whether text-based cell outputs should be wrapped.
    """,
    cmd_filter=(
        ~buffer_has_focus
        & tab_type_has_focus("euporie.notebook.tabs.notebook:Notebook")
    )
    | ~tab_type_has_focus("euporie.notebook.tabs.notebook:Notebook"),
)

add_setting(
    name="text_output_limit",
    group="euporie.core.widgets.cell_outputs",
    flags=["--text-output-limit"],
    type_=int,
    help_="Limit the amount of cell text output",
    default=1_000_000,
    schema={
        "minimum": 0,
    },
    description="""
        Limit the number of text characters in interactive cell text output to this value.
        Use ``0`` to allow any amount of characters.
    """,
)

# euporie,core.widgets.file_browser:FileBrowser

add_setting(
    name="show_file_icons",
    group="euporie.core.widgets.file_browser",
    flags=["--show-file-icons"],
    type_=bool,
    title="File icons",
    help_="Show file icons in the file manager",
    default=False,
    schema={
        "type": "boolean",
    },
    description="""
        Whether file icons should be shown in the file manager.

        These icons exist in the unicode private use area, and may require custom
        fonts such as ``awesome-terminal-fonts`` or ``nerdfonts`` to be installed.
    """,
)

add_setting(
    name="show_hidden_files",
    group="euporie.core.widgets.file_browser",
    flags=["--show-hidden-files"],
    type_=bool,
    title="Hidden files",
    help_="Show hidden files in the file manager",
    default=False,
    schema={
        "type": "boolean",
    },
    description="""
        Whether files and directories starting with a dot should be shown
        in the file manager.
    """,
)

# euporie.core.widgets.inputs:KernelInput

add_setting(
    name="line_numbers",
    group="euporie.core.widgets",
    flags=["--line-numbers"],
    type_=bool,
    help_="Show or hide line numbers",
    default=True,
    description="""
        Whether line numbers are shown by default.
    """,
    hooks=[lambda x: get_app().refresh()],
)

add_setting(
    name="relative_line_numbers",
    group="euporie.core.widgets",
    type_=bool,
    help_="Use relative line numbers",
    default=False,
    description="""
        When set to ``True``, line numbers will be displayed relative to the current
        cursor line.
    """,
    hooks=[lambda x: get_app().refresh()],
)

add_setting(
    name="autoformat",
    group="euporie.core.widgets",
    flags=["--autoformat"],
    type_=bool,
    help_="Automatically re-format code cells when run",
    default=False,
    description="""
        Whether to automatically reformat code cells before they are run.
    """,
)

add_setting(
    name="autocomplete",
    group="euporie.core.widgets",
    flags=["--autocomplete"],
    type_=bool,
    help_="Provide completions suggestions automatically",
    default=False,
    description="""
        Whether to automatically suggestion completions while typing in code cells.
    """,
)

add_setting(
    name="autosuggest",
    group="euporie.core.widgets",
    flags=["--autosuggest"],
    type_=str,
    choices=["smart", "simple", "none"],
    help_="Provide line completion suggestions",
    default="smart",
    description="""
        Whether to automatically suggestion line content while typing in code cells.
    """,
)

add_setting(
    name="autoinspect",
    group="euporie.core.widgets.inputs",
    flags=["--autoinspect"],
    type_=bool,
    help_="Display contextual help automatically",
    default=False,
    description="""
        Whether to automatically display contextual help when navigating through code cells.
    """,
)


# euporie.core.bars.status:StatusBar

add_setting(
    name="show_status_bar",
    group="euporie.core.bars.status",
    flags=["--show-status-bar"],
    type_=bool,
    title="status bar",
    help_="Show the status bar",
    default=True,
    schema={
        "type": "boolean",
    },
    description="""
        Whether the status bar should be shown at the bottom of the screen.
    """,
)

# euporie.core.widgets.decor:

add_setting(
    name="show_shadows",
    group="euporie.core.widgets.decor",
    flags=["--show-shadows"],
    type_=bool,
    help_="Show or hide shadows under menus and dialogs",
    default=True,
    description="""
        Sets whether shadows are shown under dialogs and popup-menus.
    """,
)

# euporie.core.widgets.cell

add_setting(
    name="show_cell_borders",
    group="euporie.core.widgets.cell",
    title="cell borders",
    flags=["--show-cell-borders"],
    type_=bool,
    help_="Show or hide cell borders.",
    default=False,
    schema={
        "type": "boolean",
    },
    description="""
        Whether cell borders should be drawn for unselected cells.
    """,
)

add_setting(
    name="external_editor",
    group="euporie.core.widgets.cell",
    flags=["--external-editor"],
    type_=str,
    help_="Set the external editor to use.",
    default=None,
    description="""
        A command to run when editing cells externally. The following strings in
        the command will be replaced with values which locate the cell being
        edited:

        * ``{top}``
        * ``{left}``
        * ``{bottom}``
        * ``{right}``
        * ``{width}``
        * ``{height}``

        This is useful if you run euporie inside a tmux session, and wish to launch
        your editor in a pop-up pane. This can be achieved by setting this parameter
        to something like the following:

        .. code-block::

           "tmux display-popup -x {left} -y {bottom} -w {width} -h {height} -B -E micro"

    """,
)
