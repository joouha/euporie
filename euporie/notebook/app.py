"""A text base user interface for euporie."""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING, cast

from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text.base import to_formatted_text
from prompt_toolkit.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension
from upath import UPath

from euporie.core import __logo__
from euporie.core.app import BaseApp
from euporie.core.commands import add_cmd, get_cmd
from euporie.core.config import add_setting
from euporie.core.ft.utils import truncate
from euporie.core.key_binding.registry import register_bindings
from euporie.core.tabs.base import Tab
from euporie.core.widgets.decor import Pattern
from euporie.core.widgets.dialog import (
    AboutDialog,
    ConfirmDialog,
    ErrorDialog,
    MsgBoxDialog,
    NoKernelsDialog,
    OpenFileDialog,
    SaveAsDialog,
    SelectKernelDialog,
    ShortcutsDialog,
    UnsavedDialog,
)
from euporie.core.widgets.file_browser import FileBrowser
from euporie.core.widgets.layout import TabBarControl, TabBarTab
from euporie.core.widgets.menu import MenuBar, MenuItem
from euporie.core.widgets.pager import Pager
from euporie.core.widgets.palette import CommandPalette
from euporie.core.widgets.search_bar import SearchBar
from euporie.core.widgets.status_bar import StatusBar
from euporie.notebook.enums import TabMode
from euporie.notebook.tabs import Notebook
from euporie.notebook.widgets.side_bar import SideBar

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from typing import Any, Callable, Sequence

    from prompt_toolkit.formatted_text import StyleAndTextTuples
    from prompt_toolkit.layout.containers import AnyContainer, Float

    from euporie.core.widgets.cell import Cell
    from euporie.core.widgets.status_bar import StatusBarFields

log = logging.getLogger(__name__)


class NotebookApp(BaseApp):
    """Notebook app.

    Interactively edit a notebook file.

    Launch the interactive TUI notebook editor, allowing you to run and edit Jupyter
    notebooks in the terminal.
    """

    name = "notebook"
    need_mouse_support = True

    def __init__(self, **kwargs: Any) -> None:
        """Create a new euporie text user interface application instance."""
        kwargs.setdefault("title", "euporie-notebook")
        kwargs.setdefault("full_screen", True)
        kwargs.setdefault("leave_graphics", False)
        super().__init__(**kwargs)
        self.bindings_to_load.append("euporie.notebook.app.NotebookApp")

        # Register config hooks
        self.config.get_item("show_cell_borders").event += lambda x: self.refresh()

    def statusbar_defaults(self) -> StatusBarFields | None:
        """Load the default statusbar fields (run after keybindings are loaded)."""
        return (
            [
                [
                    ("", "Press "),
                    ("bold", get_cmd("new-notebook").key_str()),
                    ("", " to start a new notebook"),
                ],
            ],
            [[("", "Press "), ("bold", get_cmd("quit").key_str()), ("", " to quit")]],
        )

    async def _poll_terminal_colors(self) -> None:
        """Repeatedly query the terminal for its background and foreground colours."""
        while self.config.terminal_polling_interval:
            await asyncio.sleep(self.config.terminal_polling_interval)
            self.term_info.colors.send()

    def post_load(self) -> None:
        """Continue loading the app."""
        super().post_load()
        # Ensure an opened tab is focused
        if self.tab:
            self.tab.focus()

        # Load style hooks and start polling terminal style
        if self.config.terminal_polling_interval and hasattr(
            self.input, "vt100_parser"
        ):
            self.create_background_task(self._poll_terminal_colors())

    def format_title(self) -> StyleAndTextTuples:
        """Format the tab's title for display in the top right of the app."""
        if self.tab:
            title = truncate(to_formatted_text(self.tab.title, style="bold"), 30)
            return [("", " "), *title, ("", " ")]
        else:
            return []

    def tab_container(self) -> AnyContainer:
        """Return a container with all opened tabs.

        Returns:
            A layout displaying the opened tab containers.

        """
        if self.tabs:
            if TabMode(self.config.tab_mode) == TabMode.TILE_HORIZONTALLY:
                return HSplit(
                    children=self.tabs,
                    padding=1,
                    padding_style="class:tab-padding",
                    padding_char="─",
                )
            elif TabMode(self.config.tab_mode) == TabMode.TILE_VERTICALLY:
                return VSplit(
                    children=self.tabs,
                    padding=1,
                    padding_style="class:tab-padding",
                    padding_char="│",
                )
            else:
                return DynamicContainer(lambda: self.tabs[self._tab_idx])
        else:
            return Pattern(
                self.config.background_character, self.config.background_pattern
            )

    def load_container(self) -> FloatContainer:
        """Build the main application layout."""
        have_tabs = Condition(lambda: bool(self.tabs))

        self.logo = Window(
            FormattedTextControl(
                [("", f" {__logo__} ")],
                focusable=~have_tabs,
                show_cursor=False,
                style="class:menu,logo",
            ),
            height=1,
            width=3,
            dont_extend_width=True,
        )

        title_bar = ConditionalContainer(
            Window(
                content=FormattedTextControl(self.format_title, show_cursor=False),
                height=1,
                style="class:menu.item",
                dont_extend_width=True,
                align=WindowAlign.RIGHT,
            ),
            filter=have_tabs,
        )

        self.tab_bar_control = TabBarControl(
            tabs=self.tab_bar_tabs,
            active=lambda: self._tab_idx,
            closeable=True,
        )
        tab_bar = ConditionalContainer(
            Window(
                self.tab_bar_control,
                height=2,
                style="class:app-tab-bar",
            ),
            filter=Condition(
                lambda: (len(self.tabs) > 1 or self.config.always_show_tab_bar)
                and TabMode(self.config.tab_mode) == TabMode.STACK
            ),
        )

        self.pager = Pager()
        self.search_bar = SearchBar()

        self.dialogs["command-palette"] = CommandPalette(self)
        self.dialogs["about"] = AboutDialog(self)
        self.dialogs["open-file"] = OpenFileDialog(self)
        self.dialogs["save-as"] = SaveAsDialog(self)
        self.dialogs["no-kernels"] = NoKernelsDialog(self)
        self.dialogs["change-kernel"] = SelectKernelDialog(self)
        self.dialogs["confirm"] = ConfirmDialog(self)
        self.dialogs["error"] = ErrorDialog(self)
        self.dialogs["unsaved"] = UnsavedDialog(self)
        self.dialogs["shortcuts"] = ShortcutsDialog(self)
        self.dialogs["msgbox"] = MsgBoxDialog(self)

        top_bar = ConditionalContainer(
            content=VSplit(
                [
                    self.logo,
                    MenuBar(app=self, menu_items=self.load_menu_items()),
                    title_bar,
                ]
            ),
            filter=self.config.filter("show_top_bar"),
        )

        titles: Sequence[str]
        icons: Sequence[str]
        panels: Sequence[AnyContainer]
        titles, icons, panels = list(
            zip(
                *[
                    (
                        "File Browser",
                        "",
                        FileBrowser(width=25, on_open=self.open_file),
                    )
                ]
            ),
        )
        self.side_bar = SideBar(titles, icons, panels)

        self.container = FloatContainer(
            content=HSplit(
                [
                    top_bar,
                    VSplit(
                        [
                            self.side_bar,
                            HSplit(
                                [
                                    tab_bar,
                                    DynamicContainer(self.tab_container),
                                    self.pager,
                                ],
                                width=Dimension(weight=1),
                            ),
                        ],
                        height=Dimension(min=1),
                    ),
                    self.search_bar,
                    StatusBar(default=self.statusbar_defaults()),
                ],
                style="class:body",
            ),
            floats=cast("list[Float]", self.floats),
        )

        return self.container

    def tab_bar_tabs(self) -> list[TabBarTab]:
        """Return a list of the current tabs for the tab-bar."""
        return [
            TabBarTab(
                title=partial(lambda x: x.title, tab),
                on_activate=partial(setattr, self, "tab_idx", i),
                on_close=partial(self.close_tab, tab),
            )
            for i, tab in enumerate(self.tabs)
        ]

    def _handle_exception(
        self, loop: AbstractEventLoop, context: dict[str, Any]
    ) -> None:
        exception = context.get("exception")
        # Also display a dialog to the user
        self.dialogs["error"].show(exception=exception)
        # Log observed exceptions to the log
        log.exception("An unhandled exception occurred", exc_info=exception)

    def exit(self, *args: Any, **kwargs: Any) -> None:
        """Check for unsaved files before closing.

        Creates a chain of close file commands, where the callback for each triggers
        the closure of the next. The closing process can be cancelled anywhere along
        the chain.

        Args:
            args: Positional arguments
            kwargs: Key word arguments

        """
        really_close = super().exit
        if self.tabs:

            def final_cb() -> None:
                """Really exit after the last tab in the chain is closed."""
                self.cleanup_closed_tab(self.tabs[0])
                really_close(*args, **kwargs)

            def create_cb(close_tab: Tab, cleanup_tab: Tab, cb: Callable) -> Callable:
                """Generate a tab close chaining callbacks.

                Cleans up after the previously closed tab, and requests to close the
                next tab in the chain.

                Args:
                    close_tab: The tab to close
                    cleanup_tab: The previously closed tab to cleanup
                    cb: The callback to call when work is complete

                Returns:
                    A callback function which cleans up `cleanup_tab` and closes
                        `close_tab`.

                """

                def inner() -> None:
                    self.cleanup_closed_tab(cleanup_tab)
                    close_tab.close(cb=cb)

                return inner

            cb = final_cb
            for close_tab, cleanup_tab in zip(self.tabs, self.tabs[1:]):
                cb = create_cb(close_tab, cleanup_tab, cb)
            self.tabs[-1].close(cb)
        else:
            really_close(*args, **kwargs)

    @property
    def notebook(self) -> Notebook | None:
        """Return the currently active notebook."""
        if isinstance(self.tab, Notebook):
            return self.tab
        return None

    @property
    def cell(self) -> Cell | None:
        """Return the currently active cell."""
        if isinstance(self.tab, Notebook):
            return self.tab.cell
        return None

    def load_menu_items(self) -> list[MenuItem]:
        """Load the list of menu items to display in the menu."""
        separator = MenuItem(separator=True)
        return [
            MenuItem(
                "File",
                children=[
                    get_cmd("new-notebook").menu,
                    get_cmd("open-file").menu,
                    separator,
                    get_cmd("save-file").menu,
                    get_cmd("save-as").menu,
                    get_cmd("close-tab").menu,
                    separator,
                    get_cmd("quit").menu,
                ],
            ),
            MenuItem(
                "Edit",
                children=[
                    get_cmd("undelete-cells").menu,
                    separator,
                    get_cmd("cut-cells").menu,
                    get_cmd("copy-cells").menu,
                    get_cmd("paste-cells").menu,
                    separator,
                    get_cmd("copy-outputs").menu,
                    get_cmd("clear-cell-outputs").menu,
                    separator,
                    get_cmd("find").menu,
                    separator,
                    get_cmd("reformat-cells").menu,
                    get_cmd("reformat-notebook").menu,
                ],
            ),
            MenuItem(
                "Run",
                children=[
                    get_cmd("run-selected-cells").menu,
                    get_cmd("run-all-cells").menu,
                ],
            ),
            MenuItem(
                "Kernel",
                children=[
                    get_cmd("interrupt-kernel").menu,
                    get_cmd("restart-kernel").menu,
                    get_cmd("change-kernel").menu,
                ],
            ),
            MenuItem(
                "Tabs",
                children=[
                    get_cmd("next-tab").menu,
                    get_cmd("previous-tab").menu,
                    separator,
                    MenuItem(
                        "Tab mode",
                        children=[
                            get_cmd(f"set-tab-mode-{choice}").menu
                            for choice in self.config.get_item("tab_mode").choices
                        ],
                    ),
                ],
            ),
            MenuItem(
                "Settings",
                children=[
                    self.config.get_item("edit_mode").menu,
                    self.config.get_item("set_cursor_shape").menu,
                    separator,
                    self.config.get_item("color_scheme").menu,
                    self.config.get_item("syntax_theme").menu,
                    get_cmd("toggle-background-pattern").menu,
                    get_cmd("toggle-show-cell-borders").menu,
                    get_cmd("toggle-tmux-graphics").menu,
                    separator,
                    get_cmd("toggle-expand").menu,
                    get_cmd("toggle-line-numbers").menu,
                    MenuItem(
                        "UI Elements",
                        children=[
                            get_cmd("toggle-always-show-tab-bar").menu,
                            get_cmd("toggle-show-side-bar").menu,
                            get_cmd("toggle-show-status-bar").menu,
                            get_cmd("toggle-show-scroll-bar").menu,
                        ],
                    ),
                    separator,
                    MenuItem(
                        "Cell formatting",
                        children=[
                            get_cmd("toggle-autoformat").menu,
                            separator,
                            get_cmd("toggle-format-black").menu,
                            get_cmd("toggle-format-isort").menu,
                            get_cmd("toggle-format-ssort").menu,
                        ],
                    ),
                    get_cmd("toggle-autocomplete").menu,
                    get_cmd("toggle-autosuggest").menu,
                    get_cmd("toggle-autoinspect").menu,
                    get_cmd("toggle-run-after-external-edit").menu,
                ],
            ),
            MenuItem(
                "Help",
                children=[
                    get_cmd("show-command-palette").menu,
                    get_cmd("keyboard-shortcuts").menu,
                    get_cmd("view-documentation").menu,
                    separator,
                    get_cmd("view-logs").menu,
                    separator,
                    get_cmd("about").menu,
                ],
            ),
        ]

    # ################################### Commands ####################################

    @staticmethod
    @add_cmd()
    def _new_notebook() -> None:
        """Create a new file."""
        from euporie.notebook.current import get_app

        app = get_app()
        app.tabs.append(Notebook(app, None))
        app.tabs[-1].focus()

    @staticmethod
    @add_cmd()
    def _view_documentation() -> None:
        """Open the documentation in a web-view tab."""
        from euporie.core.current import get_app

        get_app().open_file(UPath("https://euporie.readthedocs.io/"))

    # ################################### Settings ####################################

    add_setting(
        name="tab_mode",
        flags=["--tab-mode"],
        type_=str,
        choices=[mode.value for mode in TabMode],
        default="stack",
        help_="The method used to display multiple tabs",
        description="""
            Determines how multiple tabs are displayed when more than one tab is open.
            * ``stack`` displays one tab at a time with a tab-bar
            * ``tile_horizontally`` displays tabs side-by-side
            * ``tile_vertically`` displays tabs one-atop-the-next
        """,
    )

    add_setting(
        name="always_show_tab_bar",
        flags=["--always-show-tab-bar"],
        type_=bool,
        help_="Always show the tab bar",
        default=False,
        description="""
            When set, the tab bar will always be shown - otherwise the tab bar is only
            shown when multiple tabs are open.
        """,
    )

    add_setting(
        name="background_pattern",
        flags=["--background-pattern", "--bg-pattern"],
        type_=int,
        choices=list(range(6)),
        help_="The background pattern to use",
        default=2,
        schema={
            "minimum": 0,
            "maximum": 5,
        },
        description="""
            The background pattern to use when the notebook is narrower than the
            available width. Zero mean no pattern is used.
        """,
    )

    add_setting(
        name="background_character",
        flags=["--background-character", "--bg-char"],
        type_=str,
        help_="Character for background pattern",
        default="·",
        schema={
            "maxLength": 1,
        },
        description="""
            The character to use when drawing the background pattern.

            Recommended characters include: "·", "⬤", "╳", "╱", "╲", "░", "▒", "▓", "▞", "╬"
        """,
    )

    add_setting(
        name="run_after_external_edit",
        flags=["--run-after-external-edit"],
        type_=bool,
        help_="Run cells after editing externally",
        default=False,
        description="""
            Whether to execute a cell immediately after editing in `$EDITOR`.
        """,
    )

    add_setting(
        name="run",
        flags=["--run"],
        type_=bool,
        help_="Run the notebook files when loaded",
        default=False,
        description="""
            If set, notebooks will be run automatically when opened, or if previewing a
            file, the notebooks will be run before being output.
        """,
    )

    add_setting(
        name="show_top_bar",
        flags=["--show-top-bar"],
        type_=bool,
        title="top bar",
        help_="Show the top bar",
        default=True,
        schema={"type": "boolean"},
        description="""
            Whether the top bar should be shown at the top of the screen.
        """,
    )

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.notebook.app.NotebookApp": {
                "new-notebook": "c-n",
                "toggle-show-top-bar": ("A-m"),
            }
        }
    )
