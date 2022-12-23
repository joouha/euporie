"""Defines a sidebar."""

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
from euporie.core.key_binding.registry import register_bindings
from euporie.core.widgets.decor import Line
from euporie.core.widgets.forms import ToggleButton, ToggleButtons

if TYPE_CHECKING:
    from typing import Sequence

    from prompt_toolkit.layout.containers import AnyContainer


class SidebarButtons(ToggleButtons):
    """Vertical toggle-buttons with additional styling for the sidebar."""

    def _get_sep_style(self, i: int) -> "str":
        if self.index == i:
            return "class:sidebar,buttons,separator,selection,after"
        elif self.index == i - 1:
            return "class:sidebar,buttons,separator,selection,before"
        else:
            return "class:sidebar,buttons,separator"

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


class Sidebar:
    """A sidebar for the notebook application."""

    def __init__(
        self,
        titles: "Sequence[str]",
        icons: "Sequence[str]",
        panels: "Sequence[AnyContainer]",
    ) -> "None":
        """Initialize a new sidebar object."""
        self.sidebar_buttons = SidebarButtons(
            options=list(icons),
            style="class:buttons",
            vertical=True,
            border=None,
            multiple=True,
            max_count=1,
        )
        sidebar_hidden = Condition(lambda: bool(self.sidebar_buttons.index is None))

        self.container = VSplit(
            [
                VSplit(
                    [
                        self.sidebar_buttons,
                        ConditionalContainer(
                            Line(
                                char="▏",
                                width=1,
                                collapse=False,
                                style="class:sidebar,border,outer",
                            ),
                            filter=sidebar_hidden,
                        ),
                    ],
                ),
                ConditionalContainer(
                    VSplit(
                        [
                            Line(
                                char="▏",
                                width=1,
                                style="class:sidebar,border",
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
                                        lambda: panels[self.sidebar_buttons.index or 0]
                                    ),
                                ],
                            ),
                            Line(
                                char="▕",
                                width=1,
                                collapse=False,
                                style="class:sidebar,border",
                            ),
                        ],
                    ),
                    filter=~sidebar_hidden,
                ),
            ],
            style="class:sidebar",
        )

    def toggle(self) -> "None":
        """Toggle the visibility of the sidebar."""
        if self.sidebar_buttons.index is None:
            self.sidebar_buttons.index = 0
        else:
            self.sidebar_buttons.index = None

    def __pt_container__(self) -> "AnyContainer":
        """Return the sidebar's main container."""
        return self.container

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _toggle_sidebar() -> "None":
        """Create a new file."""
        from euporie.notebook.app import get_app

        get_app().sidebar.toggle()

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.notebook.app.NotebookApp": {
                "toggle-sidebar": "c-b",
            }
        }
    )
