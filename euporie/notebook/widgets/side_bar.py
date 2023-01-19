"""Defines a side-bar."""

from functools import partial
from typing import TYPE_CHECKING

from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import FormattedTextControl

from euporie.core.commands import add_cmd
from euporie.core.config import add_setting
from euporie.core.key_binding.registry import register_bindings
from euporie.core.widgets.decor import Line
from euporie.core.widgets.forms import ToggleButton, ToggleButtons

if TYPE_CHECKING:
    from typing import Sequence

    from prompt_toolkit.layout.containers import AnyContainer


class SideBarButtons(ToggleButtons):
    """Vertical toggle-buttons with additional styling for the side-bar."""

    def _get_sep_style(self, i: int) -> "str":
        if self.index == i:
            return "class:side_bar,buttons,separator,selection,after"
        elif self.index == i - 1:
            return "class:side_bar,buttons,separator,selection,before"
        else:
            return "class:side_bar,buttons,separator"

    def load_container(self) -> "AnyContainer":
        """Load the widget's container."""
        self.buttons: "list[ToggleButton]" = []
        children: "list[AnyContainer]" = []
        for i, (label, selected) in enumerate(zip(self.labels, self.mask)):
            children.append(
                Window(char="▄", height=1, style=partial(self._get_sep_style, i))
            )
            button = ToggleButton(
                text=label,
                selected=selected,
                on_click=partial(lambda index, button: self.toggle_item(index), i),
                border=None,
                style=self.get_button_style(i),
                disabled=self.disabled,
            )
            self.buttons.append(button)
            children.append(button)
        children.extend(
            [
                Window(
                    char="▄",
                    height=1,
                    style=partial(self._get_sep_style, len(self.options)),
                ),
                Window(),
            ]
        )
        self.on_change += self.update_buttons
        return HSplit(
            children,
            style="class:toggle-buttons",
            key_bindings=self.key_bindings(),
        )


class SideBar:
    """A side-bar for the notebook application."""

    def __init__(
        self,
        titles: "Sequence[str]",
        icons: "Sequence[str]",
        panels: "Sequence[AnyContainer]",
    ) -> "None":
        """Initialize a new side-bar object."""
        from euporie.core.current import get_app

        self.side_bar_buttons = SideBarButtons(
            options=list(icons),
            style="class:buttons",
            vertical=True,
            border=None,
            multiple=True,
            max_count=1,
        )
        pane_hidden = Condition(lambda: bool(self.side_bar_buttons.index is None))

        self.container = ConditionalContainer(
            VSplit(
                [
                    VSplit(
                        [
                            self.side_bar_buttons,
                            ConditionalContainer(
                                Line(
                                    char="▏",
                                    width=1,
                                    collapse=False,
                                    style="class:side_bar,border,outer",
                                ),
                                filter=pane_hidden,
                            ),
                        ],
                    ),
                    ConditionalContainer(
                        VSplit(
                            [
                                Line(
                                    char="▏",
                                    width=1,
                                    style="class:side_bar,border",
                                ),
                                HSplit(
                                    [
                                        Window(
                                            FormattedTextControl(
                                                [
                                                    (
                                                        "class:title,text",
                                                        " File Browser ",
                                                    )
                                                ],
                                            ),
                                            char="=",
                                            height=1,
                                            align=WindowAlign.CENTER,
                                            style="class:title",
                                        ),
                                        DynamicContainer(
                                            lambda: panels[
                                                self.side_bar_buttons.index or 0
                                            ]
                                        ),
                                    ],
                                ),
                                Line(
                                    char="▕",
                                    width=1,
                                    collapse=False,
                                    style="class:side_bar,border",
                                ),
                            ],
                        ),
                        filter=~pane_hidden,
                    ),
                ],
                style="class:side_bar",
            ),
            filter=get_app().config.filter("show_side_bar"),
        )

    def toggle_pane(self) -> "None":
        """Toggle the visibility of the side-bar."""
        if self.side_bar_buttons.index is None:
            self.side_bar_buttons.index = 0
        else:
            self.side_bar_buttons.index = None

    def __pt_container__(self) -> "AnyContainer":
        """Return the side_bar's main container."""
        return self.container

    # ################################### Settings ####################################

    add_setting(
        name="show_side_bar",
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

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _toggle_side_bar_pane() -> "None":
        """Open or close the current side-bar pane."""
        from euporie.notebook.current import get_app

        get_app().side_bar.toggle_pane()

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.notebook.app.NotebookApp": {
                "toggle-side-bar-pane": "c-b",
            }
        }
    )
