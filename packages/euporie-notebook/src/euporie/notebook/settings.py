"""Notebook app settings definitions."""

from __future__ import annotations

from euporie.core.config._setting import Setting
from euporie.notebook.enums import TabMode

tab_mode = Setting(
    name="tab_mode",
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

always_show_tab_bar = Setting(
    name="always_show_tab_bar",
    flags=["--always-show-tab-bar"],
    type_=bool,
    help_="Always show the tab bar",
    default=False,
    description="""
        When set, the tab bar will always be shown - otherwise the tab bar is only
        shown when multiple tabs are open.
    """,
)

background_pattern = Setting(
    name="background_pattern",
    flags=["--background-pattern", "--bg-pattern"],
    type_=int,
    choices={
        # No pattern
        0: lambda x, y: False,
        # Solid fill
        1: lambda x, y: True,
        2: lambda x, y: (x + y) % 2 == 0,
        3: lambda x, y: (x + 2 * y) % 4 == 0,
        # Diagonal stripes (down-left)
        4: lambda x, y: (x + y) % 3 == 0,
        5: lambda x, y: ((x + y % 2 * 3) % 6) % 4 == 0,
        # Large grid
        6: lambda x, y: x % 4 == 0 and y % 2 == 0,
        # Trellis
        7: lambda x, y: (x % 5 == 0) or (y % 3 == 0),
        # Diamond lattice
        8: lambda x, y: (x + y) % 4 == 0 or (x - y) % 4 == 0,
        # Small checkerboard
        9: lambda x, y: (x % 4 < 2) ^ (y % 2 < 1),
        # Large checkerboard
        10: lambda x, y: (x % 8 < 4) ^ (y % 4 < 2),
        # Sparse dots
        11: lambda x, y: (x % 6 in (0, 1)) and (y % 3 == 0),
    },
    help_="The background pattern to use",
    default=2,
    schema={
        "minimum": 0,
        "maximum": 11,
    },
    description="""
        The background pattern to use when the notebook is narrower than the
        available width. Zero means no pattern is used.
    """,
)

background_character = Setting(
    name="background_character",
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
    """,
)

run_after_external_edit = Setting(
    name="run_after_external_edit",
    flags=["--run-after-external-edit"],
    type_=bool,
    help_="Run cells after editing externally",
    default=False,
    description="""
        Whether to execute a cell immediately after editing in `$EDITOR`.
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

show_top_bar = Setting(
    name="show_top_bar",
    flags=["--show-top-bar"],
    type_=bool,
    title="top bar",
    help_="Show the top bar",
    default=True,
    schema={"type": "boolean"},
    description="""
        Whether the top bar should be shown at the top of the screen.
    """,
    keys=["A-m"],
)

show_side_bar = Setting(
    name="show_side_bar",
    flags=["--show-side-bar"],
    type_=bool,
    title="side-bar",
    help_="Show the side-bar",
    default=True,
    schema={
        "type": "boolean",
    },
    description="""
        Whether the side-bar should be shown at the side of the screen.
    """,
)

side_bar_width = Setting(
    name="side_bar_width",
    flags=["--side-bar-width"],
    type_=int,
    help_="Width of the side-bar",
    default=25,
    schema={
        "type": "integer",
        "minimum": 10,
        "maximum": 200,
    },
    description="""
        The width of the side-bar in characters.
    """,
)

side_bar_panel_index = Setting(
    name="side_bar_panel_index",
    type_=lambda x: int(x) if str(x).isdigit() else None,
    help_="Active side-bar panel index",
    default=0,
    choices={
        -1: None,
        **{i: i for i in range(99)},
    },
    schema={"type": ["integer"], "minimum": -1},
    description="""
        The index of the currently active side-bar panel, or ``None`` if no panel is
        active. The default "-1" selects the first panel on initial startup.
    """,
)

show_scroll_bar = Setting(
    name="show_scroll_bar",
    title="scroll bar",
    flags=["--show-scroll-bar"],
    type_=bool,
    help_="Show the scroll bar",
    default=True,
    description="""
        Whether the scroll bar should be shown on the right of the screen.
    """,
)
