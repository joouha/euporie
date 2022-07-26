"""A text base user interface for euporie."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app as ptk_get_app
from prompt_toolkit.filters import is_done
from prompt_toolkit.filters.app import renderer_height_is_known
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    Window,
)
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.menus import CompletionsMenu

from euporie.console.tabs.console import Console
from euporie.core.app import BaseApp
from euporie.core.commands import add_cmd
from euporie.core.filters import buffer_is_code, buffer_is_empty
from euporie.core.key_binding.registry import register_bindings
from euporie.core.widgets.dialog import (
    AboutDialog,
    NoKernelsDialog,
    SelectKernelDialog,
    ShortcutsDialog,
)
from euporie.core.widgets.pager import Pager
from euporie.core.widgets.palette import CommandPalette
from euporie.core.widgets.search_bar import SearchBar
from euporie.core.widgets.status_bar import StatusBar

if TYPE_CHECKING:
    from typing import Any

log = logging.getLogger(__name__)


def get_app() -> "ConsoleApp":
    """Get the current application."""
    return cast("ConsoleApp", ptk_get_app())


class ConsoleApp(BaseApp):
    """Launch an interactive console which displays rich & interactive output.

    Launches euporie console, a frontend for Jupyter kernels which displays
    rich output in the terminal.

    """

    def __init__(self, **kwargs: "Any") -> "None":
        """Create a new euporie text user interface application instance."""
        super().__init__(
            **{
                **{
                    "full_screen": False,
                    "mouse_support": True,
                    "leave_graphics": True,
                },
                **kwargs,
            }
        )
        self.search_bar = SearchBar()
        self.bindings_to_load += ["app.console"]

        self.tabs = [Console(self)]
        self.pager = Pager()

    def load_container(self) -> "FloatContainer":
        """Returns a container with all opened tabs."""
        assert self.pager is not None
        assert self.search_bar is not None
        assert self.tab is not None

        self.dialogs["competions-menu"] = Float(
            content=CompletionsMenu(
                max_height=16,
                scroll_offset=1,
            ),
            xcursor=True,
            ycursor=True,
        )
        self.dialogs["command-palette"] = CommandPalette(self)
        self.dialogs["about"] = AboutDialog(self)
        # self.dialogs["save-as"] = SaveAsDialog(self)
        self.dialogs["no-kernels"] = NoKernelsDialog(self)
        self.dialogs["change-kernel"] = SelectKernelDialog(self)
        self.dialogs["shortcuts"] = ShortcutsDialog(self)

        return FloatContainer(
            HSplit(
                [
                    self.tab,
                    ConditionalContainer(
                        HSplit(
                            [
                                Window(
                                    height=Dimension(min=1), style="class:default"
                                ),  # Fill empty space below input
                                self.pager,
                                self.search_bar,
                                StatusBar(),
                            ],
                        ),
                        filter=~self.redrawing & ~is_done & renderer_height_is_known,
                    ),
                ]
            ),
            floats=self.floats,  # type: ignore
        )

    def exit(self, **kwargs: "Any") -> "None":
        """Close all tabs on exit."""
        for tab in self.tabs:
            tab.close()
        super().exit(**kwargs)

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _clear_screen() -> "None":
        """Clears the screen and the previous output."""
        from euporie.console.tabs.console import Console

        app = get_app()
        tab = app.tab
        if isinstance(tab, Console):
            tab.output.reset()
            tab.focus()
            app.renderer.clear()

    add_cmd(
        name="end-of-file",
        filter=buffer_is_code & buffer_is_empty,
        description="Signals the end of the input, causing the console to exit.",
    )(BaseApp.quit)

    # ################################### Settings ####################################

    # ...

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "app.console": {
                "clear-screen": "c-l",
                "end-of-file": "c-d",
            }
        }
    )
