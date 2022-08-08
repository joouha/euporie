"""A text base user interface for euporie."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app as ptk_get_app
from prompt_toolkit.application.run_in_terminal import in_terminal
from prompt_toolkit.filters import is_done
from prompt_toolkit.filters.app import renderer_height_is_known
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    FloatContainer,
    HSplit,
    Window,
)
from prompt_toolkit.layout.dimension import Dimension

from euporie.console.tabs.console import Console
from euporie.core.app import BaseApp
from euporie.core.commands import add_cmd
from euporie.core.config import add_setting
from euporie.core.filters import buffer_is_code, buffer_is_empty
from euporie.core.io import patch_renderer_diff
from euporie.core.key_binding.registry import register_bindings
from euporie.core.widgets.dialog import (
    AboutDialog,
    NoKernelsDialog,
    SaveAsDialog,
    SelectKernelDialog,
    ShortcutsDialog,
)
from euporie.core.widgets.pager import Pager
from euporie.core.widgets.palette import CommandPalette
from euporie.core.widgets.search_bar import SearchBar
from euporie.core.widgets.status_bar import StatusBar

if TYPE_CHECKING:
    from typing import Any

patch_renderer_diff()

log = logging.getLogger(__name__)


def get_app() -> "ConsoleApp":
    """Get the current application."""
    return cast("ConsoleApp", ptk_get_app())


class ConsoleApp(BaseApp):
    """Console app.

    An interactive console which connects to Jupyter kernels and displays
    rich output in the terminal.

    """

    def __init__(self, **kwargs: "Any") -> "None":
        """Create a new euporie text user interface application instance."""
        self.need_mouse_support = False
        if self.config.mouse_support is not None:
            self.need_mouse_support = self.config.mouse_support
        super().__init__(
            **{
                **{
                    "full_screen": False,
                    "leave_graphics": True,
                },
                **kwargs,
            }
        )
        self.search_bar = SearchBar()
        self.bindings_to_load += ["euporie.console.app.ConsoleApp"]

        self.tabs = [Console(self)]
        self.pager = Pager()

        self.config.get_item("mouse_support").event += lambda x: setattr(
            self, "need_mouse_support", x.value
        )

    def load_container(self) -> "FloatContainer":
        """Returns a container with all opened tabs."""
        assert self.pager is not None
        assert self.search_bar is not None
        assert self.tab is not None

        self.dialogs["command-palette"] = CommandPalette(self)
        self.dialogs["about"] = AboutDialog(self)
        self.dialogs["save-as"] = SaveAsDialog(self)
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
    async def _convert_to_notebook() -> "None":
        """Convert the current console session to a notebook."""
        from euporie.notebook.app import NotebookApp
        from euporie.notebook.tabs.notebook import Notebook

        app = get_app()
        nb_app = NotebookApp()
        for tab in app.tabs:
            if isinstance(tab, Console):
                nb = Notebook(
                    app=nb_app,
                    path=tab.path,
                    kernel=tab.kernel,
                    comms=tab.comms,
                    json=tab.json,
                )
                # Set the history to the console's history
                nb.history = tab.history
                # Add the current input
                nb.add(len(nb.json["cells"]) + 1, source=tab.input_box.buffer.text)
                # Add the new notebook to the notebook app
                nb_app.tabs.append(nb)
                # Tell notebook that the kernel has already started
                nb.kernel_started()

        async with in_terminal():
            await nb_app.run_async()

        app.exit()

    @staticmethod
    @add_cmd()
    def _clear_screen() -> "None":
        """Clears the screen and the previous output."""
        app = get_app()
        tab = app.tab
        app.renderer.clear()
        if tab is not None:
            tab.reset()

    add_cmd(
        name="end-of-file",
        filter=buffer_is_code & buffer_is_empty,
        description="Signals the end of the input, causing the console to exit.",
    )(BaseApp._quit)

    # ################################### Settings ####################################

    add_setting(
        name="mouse_support",
        flags=["--mouse-support"],
        type_=bool,
        help_="Enable or disable mouse support",
        default=None,
        description="""
            When set to True, mouse support is enabled. When set to False, mouse
            support is disabled.
        """,
    )

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.console.app.ConsoleApp": {
                "clear-screen": "c-l",
                "end-of-file": "c-d",
            }
        }
    )