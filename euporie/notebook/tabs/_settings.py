"""Define settings for the notebook app tabs."""

from euporie.core.config import add_setting

add_setting(
    name="show_scroll_bar",
    group="euporie.notebook.tabs.notebook",
    title="scroll bar",
    flags=["--show-scroll-bar"],
    type_=bool,
    help_="Show the scroll bar",
    default=True,
    description="""
        Whether the scroll bar should be shown on the right of the screen.
    """,
)

add_setting(
    name="show_side_bar",
    group="euporie.notebook.widgets.side_bar",
    flags=["--show-side-bar"],
    type_=bool,
    title="side-bar",
    help_="Show the side-bar",
    default=False,
    schema={
        "type": "boolean",
    },
    description="""
        Whether the side-bar should be shown at the side of the screen.
    """,
)
