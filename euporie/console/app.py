"""A text base user interface for euporie."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app as ptk_get_app
from prompt_toolkit.application.run_in_terminal import in_terminal
from prompt_toolkit.filters.app import (
    has_completions,
    is_done,
    is_searching,
    renderer_height_is_known,
)
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.dimension import Dimension

from euporie.console.tabs.console import Console
from euporie.core import __logo__
from euporie.core.app import BaseApp
from euporie.core.commands import add_cmd
from euporie.core.config import add_setting
from euporie.core.filters import has_dialog
from euporie.core.layout.mouse import DisableMouseOnScroll
from euporie.core.widgets.dialog import (
    AboutDialog,
    NoKernelsDialog,
    SaveAsDialog,
    SelectKernelDialog,
    ShortcutsDialog,
)
from euporie.core.widgets.pager import Pager
from euporie.core.widgets.palette import CommandPalette
from euporie.core.widgets.search import SearchBar
from euporie.core.widgets.status import StatusBar

if TYPE_CHECKING:
    from typing import Any, TypeVar

    _AppResult = TypeVar("_AppResult")

log = logging.getLogger(__name__)


def get_app() -> ConsoleApp:
    """Get the current application."""
    return cast("ConsoleApp", ptk_get_app())


class ConsoleApp(BaseApp):
    """Conole app.

    An interactive console which connects to Jupyter kernels and displays
    rich output in the terminal.

    """

    name = "console"
    log_stdout_level = "ERROR"

    def __init__(self, **kwargs: Any) -> None:
        """Create a new euporie text user interface application instance."""
        # Set default application options
        kwargs.setdefault("extend_renderer_height", True)
        kwargs.setdefault("title", "euporie-console")
        kwargs.setdefault("full_screen", False)
        kwargs.setdefault("leave_graphics", True)
        kwargs.setdefault("mouse_support", self.config.filter("mouse_support"))

        # Initialize the application
        super().__init__(**kwargs)

        self.bindings_to_load += ["euporie.console.app.ConsoleApp"]

        self.tabs = []

    def _get_reserved_height(self) -> Dimension:
        if has_dialog():
            return Dimension(min=15)
        elif has_completions():
            return Dimension(min=5)
        else:
            return Dimension(min=1)

    def load_container(self) -> FloatContainer:
        """Return a container with all opened tabs."""
        self.tabs = [Console(self)]

        self.search_bar = SearchBar()
        self.pager = Pager()

        self.dialogs["command-palette"] = CommandPalette(self)
        self.dialogs["about"] = AboutDialog(self)
        self.dialogs["save-as"] = SaveAsDialog(self)
        self.dialogs["no-kernels"] = NoKernelsDialog(self)
        self.dialogs["change-kernel"] = SelectKernelDialog(self)
        self.dialogs["shortcuts"] = ShortcutsDialog(self)

        return FloatContainer(
            DisableMouseOnScroll(
                HSplit(
                    [
                        self.tabs[0],
                        ConditionalContainer(
                            HSplit(
                                [
                                    # Fill empty space below input
                                    Window(
                                        height=self._get_reserved_height,
                                        style="class:default",
                                    ),
                                    self.pager,
                                    self.search_bar,
                                    ConditionalContainer(
                                        VSplit(
                                            [
                                                Window(
                                                    char=f" {__logo__} ",
                                                    height=1,
                                                    width=3,
                                                    style="class:menu,logo",
                                                    dont_extend_width=True,
                                                ),
                                                StatusBar(),
                                            ]
                                        ),
                                        filter=~is_searching,
                                    ),
                                ],
                            ),
                            filter=~self.redrawing
                            & ~is_done
                            & renderer_height_is_known,
                        ),
                    ]
                )
            ),
            floats=self.floats,  # type: ignore
        )

    def exit(
        self,
        result: _AppResult | None = None,
        exception: BaseException | type[BaseException] | None = None,
        style: str = "",
    ) -> None:
        """Close all tabs on exit."""
        for tab in self.tabs:
            tab.close()

        if result is not None:
            super().exit(result=result, style=style)
        elif exception is not None:
            super().exit(exception=exception, style=style)
        else:
            super().exit()

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    async def _convert_to_notebook() -> None:
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

    # register_bindings({"euporie.console.app.ConsoleApp": {}})
