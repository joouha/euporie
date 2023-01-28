"""Defines a status-bar widget."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.filters.utils import to_filter
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import FormattedTextControl

from euporie.core.config import add_setting
from euporie.core.current import get_app
from euporie.core.filters import is_searching

if TYPE_CHECKING:
    from prompt_toolkit.filters.base import FilterOrBool
    from prompt_toolkit.layout.containers import AnyContainer


class StatusBar:
    """A status bar which shows the status of the current tab."""

    def __init__(self, extra_filter: "FilterOrBool" = True) -> "None":
        """Create a new status bar instance."""
        self.app = get_app()
        self.container = ConditionalContainer(
            content=VSplit(
                [
                    Window(
                        FormattedTextControl(
                            lambda: self.app.format_status(part="left")
                        ),
                        style="class:status",
                    ),
                    Window(
                        FormattedTextControl(
                            lambda: self.app.format_status(part="right")
                        ),
                        style="class:status.right",
                        align=WindowAlign.RIGHT,
                    ),
                ],
                height=1,
            ),
            filter=get_app().config.filter("show_status_bar")
            & ~is_searching
            & to_filter(extra_filter),
        )

    def __pt_container__(self) -> "AnyContainer":
        """Return the widget's container."""
        return self.container

    # ################################### Settings ####################################

    add_setting(
        name="show_status_bar",
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
