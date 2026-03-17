"""A text base user interface for euporie."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, ClassVar, cast

from apptk.application.current import get_app as ptk_get_app
from apptk.filters.app import (
    has_completions,
    has_toolbar,
    is_done,
    renderer_height_is_known,
)
from apptk.layout.containers import (
    ConditionalContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
)
from apptk.layout.dimension import Dimension
from apptk.layout.mouse import DisableMouseOnScroll
from apptk.widgets.toolbars import (
    CommandBar,
    HorizontalCompletionsMenu,
    SearchToolbar,
    StatusBar,
)

from euporie.console import settings as console_settings
from euporie.console.tabs.console import Console
from euporie.core import settings as core_settings
from euporie.core.app.app import BaseApp
from euporie.core.filters import has_dialog
from euporie.core.history import StateHistory
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

    from apptk.application.application import Application

    from euporie.core.config._setting import Setting

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

    states: ClassVar[list[Setting]] = [
        *BaseApp.states,
    ]

    settings: ClassVar[list[Setting]] = [
        *BaseApp.settings,
        # Editor
        core_settings.line_numbers,
        core_settings.relative_line_numbers,
        core_settings.autoformat,
        core_settings.autocomplete,
        core_settings.autosuggest,
        core_settings.autoinspect,
        # Appearance
        core_settings.show_status_bar,
        core_settings.show_shadows,
        # Kernel
        core_settings.record_cell_timing,
        core_settings.show_remote_inputs,
        core_settings.show_remote_outputs,
        core_settings.save_widget_state,
        # Console-specific
        console_settings.mouse_support,
        console_settings.max_stored_outputs,
        console_settings.connection_file,
    ]

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
            content=HorizontalCompletionsMenu(
                filter=has_toolbar,
                min_item_width=5,
                max_item_width=30,
                max_height=8,
                show_meta=True,
                style="class:toolbar,menu",
            ),
            ycursor=True,
            transparent=True,
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
        self.command_bar = CommandBar(
            style="class:toolbar",
            history=StateHistory("command_history"),
        )
        self.search_bar = SearchToolbar(
            forward_search_prompt=[("class:status-field", " Find: ")],
            backward_search_prompt=[("class:status-field", " Find (up): ")],
            auto_ignore_case=True,
            history=StateHistory("search_history"),
        )
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
                                    VSplit(
                                        [
                                            logo_micro,
                                            self.command_bar,
                                            self.search_bar,
                                            StatusBar(
                                                filter=(
                                                    self.config.filters.show_status_bar
                                                    & ~has_toolbar
                                                ),
                                                left_style="class:status",
                                                right_style="class:status.right",
                                                left_separator=("▌", "▐"),
                                                right_separator=("▌", "▐"),
                                            ),
                                        ]
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
