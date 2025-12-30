"""A text base user interface for euporie."""

from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, cast
from weakref import WeakKeyDictionary

from euporie.apptk.formatted_text.base import to_formatted_text
from euporie.apptk.layout.dimension import Dimension

from euporie.apptk.filters import Condition
from euporie.apptk.formatted_text.utils import truncate
from euporie.apptk.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from euporie.apptk.layout.controls import FormattedTextControl
from euporie.core.app.app import BaseApp
from euporie.core.bars.command import CommandBar
from euporie.core.bars.menu import ToolbarCompletionsMenu
from euporie.core.bars.search import SearchBar
from euporie.core.bars.status import StatusBar
from euporie.core.filters import has_tabs
from euporie.core.key_binding.registry import register_bindings
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
from euporie.core.widgets.logo import logo_micro
from euporie.core.widgets.menu import MenuBar, MenuItem
from euporie.core.widgets.minimap import MiniMap
from euporie.core.widgets.pager import Pager
from euporie.core.widgets.palette import CommandPalette
from euporie.core.widgets.toc import TableOfContents
from euporie.notebook.enums import TabMode
from euporie.notebook.widgets.side_bar import SideBar

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from collections.abc import Callable, Sequence
    from typing import Any

    from euporie.apptk.application.application import Application
    from euporie.apptk.formatted_text import StyleAndTextTuples
    from euporie.apptk.layout.containers import AnyContainer
    from euporie.core.tabs import TabRegistryEntry
    from euporie.core.tabs.base import Tab
    from euporie.core.widgets.cell import Cell
    from euporie.notebook.tabs.new import NewTab
    from euporie.notebook.tabs.notebook import Notebook

log = logging.getLogger(__name__)


class NotebookApp(BaseApp):
    """Notebook app.

    Interactively edit a notebook file.

    Launch the interactive TUI notebook editor, allowing you to run and edit Jupyter
    notebooks in the terminal.
    """

    _tab_container: AnyContainer
    new_tab: NewTab

    name = "notebook"

    def __init__(self, **kwargs: Any) -> None:
        """Create a new euporie text user interface application instance."""
        kwargs.setdefault("title", "euporie-notebook")
        kwargs.setdefault("full_screen", True)
        kwargs.setdefault("leave_graphics", False)
        super().__init__(**kwargs)
        self.bindings_to_load.append("euporie.notebook.app:NotebookApp")

        self._tab_bar_tabs: dict[int, WeakKeyDictionary[Tab, TabBarTab]] = {}
        self.on_tabs_change += self.set_tab_container

        # Register config hooks
        self.config.events.show_cell_borders += lambda x: self.refresh()
        self.config.events.tab_mode += self.set_tab_container
        self.config.events.background_pattern += self.set_tab_container
        self.config.events.background_character += self.set_tab_container

    def pre_run(self, app: Application | None = None) -> None:
        """Continue loading the app."""
        super().pre_run(app)
        # Add a toolbar completion menu
        self.menus["toolbar_completions"] = Float(
            content=ToolbarCompletionsMenu(), ycursor=True, transparent=True
        )

    @property
    def tab_registry(self) -> list[TabRegistryEntry]:
        """Return the tab registry."""
        from euporie.notebook.tabs import _TAB_REGISTRY

        return _TAB_REGISTRY

    def format_title(self) -> StyleAndTextTuples:
        """Format the tab's title for display in the top right of the app."""
        if self.tabs:
            # Get tab without re-focusing it
            tab = self.tabs[self._tab_idx]
            title = truncate(to_formatted_text(tab.title, style="bold"), 30)
            return [("", " "), *title, ("", " ")]
        else:
            return []

    def tab_container(self) -> AnyContainer:
        """Return a container with all opened tabs.

        Returns:
            A layout container displaying the opened tab containers.
        """
        try:
            return self._tab_container
        except AttributeError:
            self.set_tab_container()
            return self._tab_container

    def set_tab_container(self, app: BaseApp | None = None) -> None:
        """Set the container to use to display opened tabs."""
        tab_mode = TabMode(self.config.tab_mode)
        if not self.tabs:
            try:
                new_tab = self.new_tab
            except AttributeError:
                from euporie.notebook.tabs.new import NewTab

                new_tab = self.new_tab = NewTab(self)
            self._tab_container = new_tab
            self.layout.focus(new_tab)
        elif tab_mode == TabMode.TILE_HORIZONTALLY:
            children = []
            for tab in self.tabs:

                def _get_tab_container(tab: Tab = tab) -> Tab:
                    return tab

                children.append(DynamicContainer(_get_tab_container))
            self._tab_container = HSplit(
                children=children,
                padding=1,
                padding_style="class:tab-padding",
                padding_char="─",
            )
        elif tab_mode == TabMode.TILE_VERTICALLY:
            children = []
            for tab in self.tabs:

                def _get_tab_container(tab: Tab = tab) -> Tab:
                    return tab

                children.append(DynamicContainer(_get_tab_container))
            self._tab_container = VSplit(
                children=children,
                padding=1,
                padding_style="class:tab-padding",
                padding_char="│",
            )
        else:
            self._tab_container = HSplit(
                [
                    ConditionalContainer(
                        Window(
                            TabBarControl(
                                tabs=self.tab_bar_tabs, active=lambda: self._tab_idx
                            ),
                            height=2,
                            style="class:app-tab-bar",
                            dont_extend_height=True,
                        ),
                        filter=Condition(
                            lambda: (
                                len(self.tabs) > 1 or self.config.always_show_tab_bar
                            )
                            and TabMode(self.config.tab_mode) == TabMode.STACK
                        ),
                    ),
                    DynamicContainer(lambda: self.tabs[self._tab_idx]),
                ]
            )

    def load_container(self) -> FloatContainer:
        """Build the main application layout."""
        title_bar = ConditionalContainer(
            Window(
                content=FormattedTextControl(self.format_title, show_cursor=False),
                height=1,
                style="class:menu.item",
                dont_extend_width=True,
                align=WindowAlign.RIGHT,
            ),
            filter=has_tabs,
        )

        self.pager = Pager()
        self.search_bar = SearchBar()
        self.command_bar = CommandBar()

        self.dialog_classes = {
            "command-palette": CommandPalette,
            "about": AboutDialog,
            "open-file": OpenFileDialog,
            "save-as": SaveAsDialog,
            "no-kernels": NoKernelsDialog,
            "change-kernel": SelectKernelDialog,
            "confirm": ConfirmDialog,
            "error": ErrorDialog,
            "unsaved": UnsavedDialog,
            "shortcuts": ShortcutsDialog,
            "msgbox": MsgBoxDialog,
        }

        top_bar = ConditionalContainer(
            content=VSplit(
                [
                    logo_micro,
                    MenuBar(app=self, menu_items=self.load_menu_items()),
                    title_bar,
                ]
            ),
            filter=self.config.filters.show_top_bar,
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
                        FileBrowser(
                            on_open=self.open_file,
                            show_hidden=self.config.filters.show_hidden_files,
                            show_icons=self.config.filters.show_file_icons,
                        ),
                    ),
                    ("Table of Contents", "", TableOfContents()),
                    ("Mini Map", "", MiniMap()),
                ]
            ),
        )

        self.side_bar = SideBar(
            titles,
            icons,
            panels,
            width=self.config.side_bar_width,
            index=self.config.side_bar_panel_index,
            on_resize=lambda s: setattr(self.config, "side_bar_width", s.width),
            on_change=lambda s: setattr(self.config, "side_bar_panel_index", s.index),
        )

        self.container = FloatContainer(
            content=HSplit(
                [
                    top_bar,
                    VSplit(
                        [
                            self.side_bar,
                            HSplit(
                                [
                                    DynamicContainer(self.tab_container),
                                    self.pager,
                                ],
                                width=Dimension(weight=1),
                            ),
                        ],
                        height=Dimension(min=1),
                    ),
                    self.command_bar,
                    self.search_bar,
                    StatusBar(),
                ],
                style="class:body",
            ),
            floats=cast("list[Float]", self.floats),
        )

        return self.container

    def tab_bar_tabs(self) -> list[TabBarTab]:
        """Return a list of the current tabs for the tab-bar."""
        result = []
        for i, tab in enumerate(self.tabs):
            index_dict = self._tab_bar_tabs.setdefault(i, WeakKeyDictionary())
            if tab not in index_dict:
                index_dict[tab] = TabBarTab(
                    title=lambda tab=tab: tab.title,  # type: ignore [misc]
                    on_activate=partial(setattr, self, "tab_idx", i),
                    on_close=partial(self.close_tab, tab),
                    closeable=True,
                )
            result.append(self._tab_bar_tabs[i][tab])
        return result

    def _handle_exception(
        self, loop: AbstractEventLoop, context: dict[str, Any]
    ) -> None:
        exception = context.get("exception")
        # Also display a dialog to the user
        if dialog := self.get_dialog("error"):
            dialog.show(exception=exception)
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
        from euporie.notebook.tabs.notebook import Notebook

        if isinstance(self.tab, Notebook):
            return self.tab
        return None

    @property
    def cell(self) -> Cell | None:
        """Return the currently active cell."""
        from euporie.notebook.tabs.notebook import Notebook

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
                    MenuItem(
                        "New",
                        children=[
                            MenuItem.from_cmd("new-notebook"),
                            separator,
                            MenuItem.from_cmd("new-console"),
                            MenuItem.from_cmd("new-text-file"),
                        ],
                    ),
                    MenuItem.from_cmd("open-file"),
                    separator,
                    MenuItem.from_cmd("save-file"),
                    MenuItem.from_cmd("save-as"),
                    MenuItem.from_cmd("close-tab"),
                    separator,
                    MenuItem.from_cmd("quit"),
                ],
                description="File management",
            ),
            MenuItem(
                "Edit",
                children=[
                    MenuItem.from_cmd("undelete-cells"),
                    separator,
                    MenuItem.from_cmd("cut-cells"),
                    MenuItem.from_cmd("copy-cells"),
                    MenuItem.from_cmd("paste-cells"),
                    separator,
                    MenuItem.from_cmd("copy-outputs"),
                    MenuItem.from_cmd("clear-cell-outputs"),
                    separator,
                    MenuItem.from_cmd("find"),
                    separator,
                    MenuItem.from_cmd("reformat-cells"),
                    MenuItem.from_cmd("reformat-notebook"),
                ],
                description="Make changes to the current file",
            ),
            MenuItem(
                "Run",
                children=[
                    MenuItem.from_cmd("run-selected-cells"),
                    MenuItem.from_cmd("run-all-cells"),
                ],
                description="Run notebook cells",
            ),
            MenuItem(
                "Kernel",
                children=[
                    MenuItem.from_cmd("interrupt-kernel"),
                    MenuItem.from_cmd("restart-kernel"),
                    MenuItem.from_cmd("change-kernel"),
                ],
                description="Manage the current notebook's kernel",
            ),
            MenuItem(
                "Tabs",
                children=[
                    MenuItem.from_cmd("next-tab"),
                    MenuItem.from_cmd("previous-tab"),
                    separator,
                    MenuItem(
                        "Tab mode",
                        children=[
                            MenuItem.from_cmd(f"set-tab-mode-{choice}")
                            for choice in self.config.choices.tab_mode
                        ],
                    ),
                ],
                description="Tab management",
            ),
            MenuItem(
                "Settings",
                children=[
                    MenuItem(
                        "UI Elements",
                        children=[
                            MenuItem.from_cmd("switch-background-pattern"),
                            MenuItem.from_cmd("toggle-show-cell-borders"),
                            MenuItem.from_cmd("toggle-always-show-tab-bar"),
                            MenuItem.from_cmd("toggle-show-side-bar"),
                            MenuItem.from_cmd("toggle-show-status-bar"),
                            MenuItem.from_cmd("toggle-show-scroll-bar"),
                            MenuItem.from_cmd("toggle-multiplexer-passthrough"),
                        ],
                        description="Turn elements of euporie's interface on or off",
                    ),
                    self.config.menus.color_scheme,
                    MenuItem(
                        "Syntax highlighting",
                        children=[
                            self.config.menus.syntax_highlighting,
                            separator,
                            *self.config.menus.syntax_theme.children,
                        ],
                        description="Configure syntax highlighting",
                    ),
                    MenuItem.from_cmd("toggle-expand"),
                    MenuItem.from_cmd("toggle-line-numbers"),
                    self.config.menus.set_cursor_shape,
                    separator,
                    self.config.menus.edit_mode,
                    separator,
                    MenuItem(
                        "Code tools",
                        children=[
                            MenuItem.from_cmd("toggle-enable-language-servers"),
                            separator,
                            self.config.menus.autosuggest,
                            MenuItem.from_cmd("toggle-autoformat"),
                            MenuItem.from_cmd("toggle-autocomplete"),
                            MenuItem.from_cmd("toggle-autoinspect"),
                        ],
                        description="Turn code assistance tools on or off",
                    ),
                    MenuItem.from_cmd("toggle-run-after-external-edit"),
                ],
                description="Make changes to euporie's configuration",
            ),
            MenuItem(
                "Help",
                children=[
                    MenuItem.from_cmd("show-command-palette"),
                    MenuItem.from_cmd("keyboard-shortcuts"),
                    MenuItem.from_cmd("view-documentation"),
                    separator,
                    MenuItem.from_cmd("view-logs"),
                    separator,
                    MenuItem.from_cmd("about"),
                ],
                description="Get help",
            ),
        ]

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.notebook.app:NotebookApp": {
                "new-notebook": "c-n",
                "toggle-show-top-bar": ("A-m"),
                "toggle-side-bar-pane": "c-b",
            }
        }
    )
