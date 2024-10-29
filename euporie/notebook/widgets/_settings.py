"""Define settings for the notebook app widgets."""

from euporie.core.config import add_setting

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
