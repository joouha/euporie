"""Define settings for the notebook app."""

from euporie.core.config import add_setting
from euporie.notebook.enums import TabMode

add_setting(
    name="tab_mode",
    group="euporie.notebook.app",
    flags=["--tab-mode"],
    type_=str,
    choices=[mode.value for mode in TabMode],
    default="stack",
    help_="The method used to display multiple tabs",
    description="""
        Determines how multiple tabs are displayed when more than one tab is open.
        * ``stack`` displays one tab at a time with a tab-bar
        * ``tile_horizontally`` displays tabs side-by-side
        * ``tile_vertically`` displays tabs one-atop-the-next
    """,
)

add_setting(
    name="always_show_tab_bar",
    group="euporie.notebook.app",
    flags=["--always-show-tab-bar"],
    type_=bool,
    help_="Always show the tab bar",
    default=False,
    description="""
        When set, the tab bar will always be shown - otherwise the tab bar is only
        shown when multiple tabs are open.
    """,
)

add_setting(
    name="background_pattern",
    group="euporie.notebook.app",
    flags=["--background-pattern", "--bg-pattern"],
    type_=int,
    choices=list(range(6)),
    help_="The background pattern to use",
    default=2,
    schema={
        "minimum": 0,
        "maximum": 5,
    },
    description="""
        The background pattern to use when the notebook is narrower than the
        available width. Zero mean no pattern is used.
    """,
)

add_setting(
    name="background_character",
    group="euporie.notebook.app",
    flags=["--background-character", "--bg-char"],
    type_=str,
    help_="Character for background pattern",
    default="·",
    schema={
        "maxLength": 1,
    },
    description="""
        The character to use when drawing the background pattern.

        Recommended characters include: "·", "⬤", "╳", "╱", "╲", "░", "▒", "▓", "▞", "╬"
    """,  # ,
)

add_setting(
    name="run_after_external_edit",
    group="euporie.notebook.app",
    flags=["--run-after-external-edit"],
    type_=bool,
    help_="Run cells after editing externally",
    default=False,
    description="""
        Whether to execute a cell immediately after editing in `$EDITOR`.
    """,
)

add_setting(
    name="run",
    group="euporie.notebook.app",
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
    name="show_top_bar",
    group="euporie.notebook.app",
    flags=["--show-top-bar"],
    type_=bool,
    title="top bar",
    help_="Show the top bar",
    default=True,
    schema={"type": "boolean"},
    description="""
        Whether the top bar should be shown at the top of the screen.
    """,
)
