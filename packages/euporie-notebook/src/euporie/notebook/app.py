"""A text base user interface for euporie."""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, ClassVar, cast

from apptk.border import OuterHalfGrid
from apptk.filters.app import has_toolbar
from apptk.formatted_text.base import to_formatted_text
from apptk.formatted_text.utils import truncate
from apptk.layout.containers import (
    ConditionalContainer,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from apptk.layout.controls import FormattedTextControl
from apptk.layout.dimension import Dimension
from apptk.widgets.docking import DockingSplit
from apptk.widgets.menus import MenuContainer, MenuItem
from apptk.widgets.panel import Panel
from apptk.widgets.toolbars import (
    CommandBar,
    HorizontalCompletionsMenu,
    SearchToolbar,
    StatusBar,
)

from euporie.core import settings as core_settings
from euporie.core.app.app import BaseApp
from euporie.core.filters import has_panes
from euporie.core.history import StateHistory
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
from euporie.core.widgets.logo import logo_micro
from euporie.core.widgets.minimap import MiniMap
from euporie.core.widgets.pager import Pager
from euporie.core.widgets.palette import CommandPalette
from euporie.core.widgets.toc import TableOfContents
from euporie.core.widgets.variables import VariableList
from euporie.notebook import settings as notebook_settings
from euporie.notebook.widgets.side_bar import SideBar

if TYPE_CHECKING:
    from asyncio import AbstractEventLoop
    from collections.abc import Callable, Sequence
    from typing import Any

    from apptk.application.application import Application
    from apptk.formatted_text import StyleAndTextTuples
    from apptk.layout.containers import AnyContainer

    from euporie.core.app.app import BaseApp as _BaseApp
    from euporie.core.config._setting import Setting
    from euporie.core.panes import PaneRegistryEntry
    from euporie.core.panes.base import Pane
    from euporie.core.widgets.cell import Cell
    from euporie.notebook.panes.new import NewPane
    from euporie.notebook.panes.notebook import Notebook

log = logging.getLogger(__name__)


class NotebookApp(BaseApp):
    """Notebook app.

    Interactively edit a notebook file.

    Launch the interactive TUI notebook editor, allowing you to run and edit Jupyter
    notebooks in the terminal.
    """

    new_pane: NewPane

    name = "notebook"

    states: ClassVar[list[Setting]] = [
        *BaseApp.states,
        notebook_settings.side_bar_width,
        notebook_settings.side_bar_panel_index,
        notebook_settings.tip_offset,
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
        core_settings.autopair,
        core_settings.external_editor,
        # Appearance
        core_settings.show_status_bar,
        core_settings.show_shadows,
        core_settings.show_cell_borders,
        core_settings.show_shadows,
        core_settings.max_notebook_width,
        core_settings.expand,
        core_settings.show_icons,
        core_settings.show_hidden_files,
        # Kernel
        core_settings.record_cell_timing,
        core_settings.show_remote_inputs,
        core_settings.show_remote_outputs,
        core_settings.save_widget_state,
        # Notebook-specific
        notebook_settings.always_show_tab_bar,
        notebook_settings.background_pattern,
        notebook_settings.background_character,
        notebook_settings.run_after_external_edit,
        notebook_settings.run,
        notebook_settings.show_top_bar,
        notebook_settings.show_side_bar,
        notebook_settings.show_scroll_bar,
    ]

    commands = (
        *BaseApp.commands,
        "new-notebook",
        "toggle-show-top-bar",
        "toggle-side-bar-pane",
        "zoom-minimap-in",
        "zoom-minimap-out",
        "tile-tabs",
        "stack-tabs",
    )

    def __init__(self, **kwargs: Any) -> None:
        """Create a new euporie text user interface application instance."""
        kwargs.setdefault("title", "euporie-notebook")
        kwargs.setdefault("full_screen", True)
        kwargs.setdefault("leave_graphics", False)
        super().__init__(**kwargs)

        self.docking_split: DockingSplit | None = None
        self.on_tabs_change += self._on_tabs_change

        # Register config hooks
        self.config.events.show_cell_borders += lambda x: self.refresh()
        self.config.events.background_pattern += lambda x: self.invalidate()
        self.config.events.background_character += lambda x: self.invalidate()

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

    @property
    def tab_registry(self) -> list[PaneRegistryEntry]:
        """Return the pane registry."""
        from euporie.notebook.panes import _PANE_REGISTRY

        return _PANE_REGISTRY

    def format_title(self) -> StyleAndTextTuples:
        """Format the pane's title for display in the top right of the app."""
        if self.panes:
            # Get tab without re-focusing it
            tab = self.pane
            title = truncate(to_formatted_text(tab.title, style="bold"), 30)
            return [("", " "), *title, ("", " ")]
        else:
            return []

    def tab_container(self) -> AnyContainer:
        """Return a container with all opened tabs.

        Returns:
            A layout container displaying the opened tab containers.
        """
        if not self.panes:
            try:
                return self.new_pane
            except AttributeError:
                from euporie.notebook.panes.new import NewPane

                self.new_pane = NewPane(self)
                self.layout.focus(self.new_pane)
                return self.new_pane

        if self.docking_split is None:
            # Initialize the DockingSplit with current tabs
            self.docking_split = DockingSplit(
                panels=[self._create_docking_panel(tab) for tab in self.panes],
                style="class:app",
                zone_color=self.color_palette.bg,
                zone_highlight=self.color_palette.hl,
                hide_single_tab=~self.config.filters.always_show_tab_bar,
                activate_on_focus=True,
            )

        return self.docking_split

    def _create_docking_panel(self, pane: Pane) -> Panel:
        """Create a Panel wrapping a Pane.

        Args:
            pane: The tab to wrap.

        Returns:
            A Panel for the pane.
        """
        return Panel(
            title=lambda pane=pane: pane.title,
            content=pane,
            closeable=True,
            on_close=lambda sender, pane=pane: self.close_tab(pane),
        )

    def _on_tabs_change(self, app: _BaseApp | None = None) -> None:
        """Handle tabs list changes."""
        if not self.panes:
            self.docking_split = None
        self.invalidate()

    def _remove_tab_from_docking(self, pane: Pane) -> None:
        """Remove a Pane's panel from the docking tree.

        Args:
            pane: The pane to remove.
        """
        if self.docking_split is None:
            return

        # Find the panel corresponding to this pane
        panel_to_remove: Panel | None = None
        for panel in self.docking_split.panels:
            if panel.content is pane:
                panel_to_remove = panel
                break

        if panel_to_remove is not None:
            self.docking_split.remove_panel(panel_to_remove)

    def add_tab(self, pane: Pane) -> None:
        """Add a pane to the app and docking split.

        Args:
            pane: The pane to add.
        """
        super().add_tab(pane)
        if self.docking_split is not None:
            panel = self._create_docking_panel(pane)
            self.docking_split.add_panel(panel)

    def replace_tab(self, old: Pane, new: Pane) -> None:
        """Replace a pane, updating its panel in the docking split.

        Args:
            old: The pane to replace (e.g. a placeholder).
            new: The pane to replace it with.
        """
        super().replace_tab(old, new)
        if self.docking_split is not None:
            for panel in self.docking_split.panels:
                if panel.content is old:
                    panel.content = new
                    panel.title = lambda new=new: new.title
                    break
            else:
                self.docking_split.add_panel(self._create_docking_panel(new))
        self.invalidate()

    def cleanup_closed_tab(self, pane: Pane) -> None:
        """Remove a pane from the app and docking split.

        Args:
            pane: The closed pane to clean up.
        """
        # Remove from docking split
        if self.docking_split is not None:
            self._remove_tab_from_docking(pane)
        # Call parent (removes from self.panes, fires on_tabs_change, focuses next)
        super().cleanup_closed_tab(pane)
        # If no panes remain, clear docking split so NewPane shows
        if not self.panes:
            self.docking_split = None

    @property
    def pane(self) -> Pane | None:
        """Return the currently selected pane."""
        return super().pane

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
            filter=has_panes,
        )

        self.pager = Pager()
        self.search_bar = SearchToolbar(
            forward_search_prompt=[("class:status-field", " Find: ")],
            backward_search_prompt=[("class:status-field", " Find (up): ")],
            auto_ignore_case=True,
            history=StateHistory("search_history"),
        )

        self.command_bar = CommandBar(
            style="class:toolbar",
            history=StateHistory("command_history"),
        )

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

        menu_bar = MenuContainer(
            menu_items=self.load_menu_items(),
            grid=OuterHalfGrid,
            padding=0,
            icons=self.config.filters.show_icons,
            shadows=self.config.filters.show_shadows,
        )
        top_bar = ConditionalContainer(
            content=VSplit([logo_micro, menu_bar, title_bar]),
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
                        lambda: "" if self.config.show_icons else [("bold", "F")],
                        FileBrowser(
                            on_chdir=os.chdir,
                            on_open=self.open_file,
                            show_hidden=self.config.filters.show_hidden_files,
                            show_icons=self.config.filters.show_icons,
                        ),
                    ),
                    (
                        "Table of Contents",
                        lambda: "" if self.config.show_icons else [("bold", "T")],
                        TableOfContents(_shadows=self.config.filters.show_shadows),
                    ),
                    (
                        "Mini Map",
                        lambda: "" if self.config.show_icons else [("bold", "M")],
                        MiniMap(),
                    ),
                    (
                        "Variables",
                        lambda: "󰞄" if self.config.show_icons else [("bold", "V")],
                        VariableList(lambda: getattr(self.pane, "kernel", None)),
                    ),
                ]
            ),
        )

        self.side_bar = SideBar(
            titles,
            icons,
            panels,
            width=self.state.side_bar_width,
            index=self.state.side_bar_panel_index,
            on_resize=lambda s: setattr(self.state, "side_bar_width", s.width),
            on_change=lambda s: setattr(self.state, "side_bar_panel_index", s.index),
        )

        def _sync_sidebar_index(setting: Setting) -> None:
            if self.side_bar.index != self.state.side_bar_panel_index:
                self.side_bar.index = self.state.side_bar_panel_index

        self.state.events.side_bar_panel_index += _sync_sidebar_index

        def _sync_sidebar_width(setting: Setting) -> None:
            if self.side_bar.width != self.state.side_bar_width:
                self.side_bar.width = self.state.side_bar_width

        self.state.events.side_bar_width += _sync_sidebar_width

        self.container = FloatContainer(
            content=HSplit(
                [
                    top_bar,
                    VSplit(
                        [
                            ConditionalContainer(
                                self.side_bar,
                                filter=self.config.filters.show_side_bar,
                            ),
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
                    StatusBar(
                        filter=(self.config.filters.show_status_bar & ~has_toolbar),
                        left_style="class:status",
                        right_style="class:status.right",
                        left_separator=("▌", "▐"),
                        right_separator=("▌", "▐"),
                    ),
                ],
                style="class:body",
            ),
            floats=cast("list[Float]", self.floats),
        )

        return self.container

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
        if self.panes:

            def final_cb() -> None:
                """Really exit after the last tab in the chain is closed."""
                self.cleanup_closed_tab(self.panes[0])
                really_close(*args, **kwargs)

            def create_cb(close_tab: Pane, cleanup_tab: Pane, cb: Callable) -> Callable:
                """Generate a pane close chaining callbacks.

                Cleans up after the previously closed pane, and requests to close the
                next tab in the chain.

                Args:
                    close_tab: The pane to close
                    cleanup_tab: The previously closed pane to cleanup
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
            for close_tab, cleanup_tab in zip(self.panes, self.panes[1:]):
                cb = create_cb(close_tab, cleanup_tab, cb)
            self.panes[-1].close(cb)
        else:
            really_close(*args, **kwargs)

    @property
    def notebook(self) -> Notebook | None:
        """Return the currently active notebook."""
        from euporie.notebook.panes.notebook import Notebook

        if isinstance(self.pane, Notebook):
            return self.pane
        return None

    @property
    def cell(self) -> Cell | None:
        """Return the currently active cell."""
        from euporie.notebook.panes.notebook import Notebook

        if isinstance(self.pane, Notebook):
            return self.pane.cell
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
                            MenuItem.from_cmd("new-console"),
                            MenuItem.from_cmd("new-terminal"),
                            separator,
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
                    MenuItem.from_cmd("tile-tabs"),
                    MenuItem.from_cmd("stack-tabs"),
                ],
                description="Tab management",
            ),
            MenuItem(
                "Settings",
                children=[
                    MenuItem(
                        "UI elements",
                        children=[
                            MenuItem.from_cmd("switch-background-pattern"),
                            MenuItem.from_cmd("toggle-show-cell-borders"),
                            MenuItem.from_cmd("toggle-show-top-bar"),
                            MenuItem.from_cmd("toggle-always-show-tab-bar"),
                            MenuItem.from_cmd("toggle-show-side-bar"),
                            MenuItem.from_cmd("toggle-show-status-bar"),
                            MenuItem.from_cmd("toggle-show-scroll-bar"),
                            MenuItem.from_cmd("toggle-show-icons"),
                            MenuItem.from_cmd("toggle-show-shadows"),
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
                            MenuItem.from_cmd("toggle-autopair"),
                        ],
                        description="Turn code assistance tools on or off",
                    ),
                    MenuItem.from_cmd("toggle-run-after-external-edit"),
                    separator,
                    MenuItem.from_cmd("open-config-file"),
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
