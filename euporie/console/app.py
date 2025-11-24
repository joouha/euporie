"""A text base user interface for euporie."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from prompt_toolkit.application.current import get_app as ptk_get_app
from prompt_toolkit.filters.app import (
    has_completions,
    is_done,
    is_searching,
    renderer_height_is_known,
)
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from prompt_toolkit.layout.dimension import Dimension

from euporie.console.tabs.console import Console
from euporie.core.app.app import BaseApp
from euporie.core.bars.command import CommandBar
from euporie.core.bars.menu import ToolbarCompletionsMenu
from euporie.core.bars.search import SearchBar
from euporie.core.bars.status import StatusBar
from euporie.core.filters import has_dialog
from euporie.core.layout.mouse import DisableMouseOnScroll
from euporie.core.widgets.dialog import (
    AboutDialog,
    ConfirmDialog,
    NoKernelsDialog,
    SaveAsDialog,
    SelectKernelDialog,
    ShortcutsDialog,
)
from euporie.core.widgets.logo import logo_micro
from euporie.core.widgets.pager import Pager
from euporie.core.widgets.palette import CommandPalette

if TYPE_CHECKING:
    from typing import Any, TypeVar

    from prompt_toolkit.application.application import Application

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

    def __init__(self, **kwargs: Any) -> None:
        """Create a new euporie text user interface application instance."""
        # Set default application options
        kwargs.setdefault("extend_renderer_height", True)
        kwargs.setdefault("title", "euporie-console")
        kwargs.setdefault("full_screen", False)
        kwargs.setdefault("leave_graphics", True)
        kwargs.setdefault("mouse_support", self.config.filters.mouse_support)

        # Initialize the application
        super().__init__(**kwargs)

        self.bindings_to_load += ["euporie.console.app:ConsoleApp"]

        self.tabs = []

    def pre_run(self, app: Application | None = None) -> None:
        """Continue loading the app."""
        super().pre_run(app)
        # Add a toolbar completion menu
        self.menus["toolbar_completions"] = Float(
            content=ToolbarCompletionsMenu(), ycursor=True, transparent=True
        )

    def _get_reserved_height(self) -> Dimension:
        if has_dialog():
            return Dimension(min=15)
        elif has_completions():
            return Dimension(min=5)
        else:
            return Dimension(min=1)

    def load_container(self) -> FloatContainer:
        """Return a container with all opened tabs."""
        self.command_bar = CommandBar()
        self.search_bar = SearchBar()
        self.pager = Pager()

        self.dialogs["command-palette"] = CommandPalette(self)
        self.dialogs["about"] = AboutDialog(self)
        self.dialogs["save-as"] = SaveAsDialog(self)
        self.dialogs["no-kernels"] = NoKernelsDialog(self)
        self.dialogs["change-kernel"] = SelectKernelDialog(self)
        self.dialogs["shortcuts"] = ShortcutsDialog(self)
        self.dialogs["confirm"] = ConfirmDialog(self)

        self.tabs = [Console(self)]

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
                                    ConditionalContainer(
                                        VSplit(
                                            [
                                                logo_micro,
                                                self.command_bar,
                                                self.search_bar,
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

    # ################################# Key Bindings ##################################

    # register_bindings({"euporie.console.app:ConsoleApp": {}})
