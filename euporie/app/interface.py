# -*- coding: utf-8 -*-
"""Contains the main Application class which runs euporie."""
from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, Callable

from prompt_toolkit.clipboard import Clipboard, InMemoryClipboard
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.layout import (
    ConditionalContainer,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.widgets import MenuContainer, MenuItem
from pygments.styles import get_all_styles  # type: ignore
from pyperclip import determine_clipboard  # type: ignore

from euporie import __logo__
from euporie.app.dialog import DialogMixin
from euporie.config import config
from euporie.containers import ScrollingContainer
from euporie.keys import KeyBindingsInfo
from euporie.menu import SmartMenuItem
from euporie.notebook import Notebook
from euporie.tab import Tab

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer

log = logging.getLogger(__name__)


class InterfaceMixin(DialogMixin):
    """Provides user interface."""

    pre_run: "list[Callable]"
    tab_op: "Callable"
    tabs: "list[Tab]"
    tab: "AnyContainer"
    is_tab_open: "Condition"
    close_tab: "Callable"
    update_style: "Callable"
    cleanup_closed_tab: "Callable"
    exit: "Callable"
    # output: "Optional[Output]"

    def setup(self) -> "None":
        """Create an output and set pre-run commands."""
        # Create an output
        self.output = create_output()
        # Set clipboard to use pyperclip if possible
        self.clipboard: "Clipboard"
        if determine_clipboard()[0]:
            self.clipboard = PyperclipClipboard()
        else:
            self.clipboard = InMemoryClipboard()

    def tab_container(self) -> "AnyContainer":
        """Returns a container with all opened tabs.

        A 1 column window is added to the left as padding.

        Returns:
            A vertical split containing the opened tab containers.

        """
        return VSplit([Window(width=1), *self.tabs])

    def layout_container(self) -> "AnyContainer":
        """Builds the main application layout."""
        kernel_status_repr = {
            "starting": "◍",
            "idle": "○",
            "busy": "●",
            "error": "☹",
        }

        def get_statusbar_text() -> "list[tuple[str, str]]":
            """Generates the formatted text for the statusbar."""
            tab = self.tab
            if isinstance(tab, Notebook):
                assert tab.kernel is not None
                kernel_status = kernel_status_repr.get(tab.kernel.status, "◌")
                assert isinstance(tab.page, ScrollingContainer)
                selected_cell = tab.page.selected_index + 1
                dirt = "*" if tab.dirty else ""
                return [
                    ("class:menu-bar.item", f" Cell {selected_cell} "),
                    ("", " "),
                    ("class:menu-bar.item bold", f" {dirt}{tab.path.name} "),
                    ("", " "),
                    ("class:menu-bar.item", f" {tab.kernel_name} {kernel_status} "),
                ]
            else:
                return []

        status_bar_text = FormattedTextControl(
            get_statusbar_text, focusable=True, show_cursor=False
        )
        self.status_bar = ConditionalContainer(
            Window(
                content=status_bar_text,
                height=D.exact(1),
                style="class:menu-bar",
                dont_extend_width=True,
                align=WindowAlign.RIGHT,
            ),
            filter=self.is_tab_open,
        )

        self.body_container = MenuContainer(
            body=DynamicContainer(self.tab_container),
            menu_items=[
                MenuItem(
                    " File ",
                    children=[
                        MenuItem(
                            "New", handler=lambda: self.ask_open_file(validate=False)
                        ),
                        MenuItem("Open", handler=self.ask_open_file),
                        MenuItem("-", disabled=True),
                        SmartMenuItem(
                            "Save",
                            handler=lambda: self.tab_op("save"),
                            disabler=~self.is_tab_open,
                        ),
                        SmartMenuItem(
                            "Close",
                            handler=self.close_tab,
                            disabler=~self.is_tab_open,
                        ),
                        MenuItem("-", disabled=True),
                        MenuItem("Exit", handler=self.try_to_exit),
                    ],
                ),
                MenuItem(
                    " Edit ",
                    children=[
                        SmartMenuItem(
                            "Cut Cell",
                            handler=lambda: self.tab_op("cut"),
                            disabler=~self.is_tab_open,
                        ),
                        SmartMenuItem(
                            "Copy Cell",
                            handler=lambda: self.tab_op("copy"),
                            disabler=~self.is_tab_open,
                        ),
                        SmartMenuItem(
                            "Paste Cell",
                            handler=lambda: self.tab_op("paste"),
                            disabler=~self.is_tab_open,
                        ),
                    ],
                ),
                MenuItem(
                    " Run ",
                    children=[
                        MenuItem(
                            "Run Cell",
                            handler=lambda: self.tab_op("run_cell"),
                        ),
                        MenuItem(
                            "Run All Cells",
                            handler=lambda: self.tab_op("run_all"),
                        ),
                    ],
                ),
                MenuItem(
                    " Kernel ",
                    children=[
                        SmartMenuItem(
                            "Interupt Kernel",
                            handler=lambda: self.tab_op("interrupt_kernel"),
                            disabler=~self.is_tab_open,
                        ),
                        SmartMenuItem(
                            "Restart Kernel",
                            handler=lambda: self.tab_op("restart_kernel"),
                            disabler=~self.is_tab_open,
                        ),
                        SmartMenuItem(
                            "Change Kernel...",
                            handler=lambda: self.tab_op("change_kernel"),
                            disabler=~self.is_tab_open,
                        ),
                    ],
                ),
                MenuItem(
                    " Settings ",
                    children=[
                        MenuItem(
                            "Syntax Theme",
                            children=[
                                SmartMenuItem(
                                    style,
                                    handler=partial(self.update_style, style),
                                    toggler=Condition(
                                        partial(
                                            lambda x: config.syntax_theme == x, style
                                        )
                                    ),
                                )
                                for style in sorted(get_all_styles())
                            ],
                        ),
                        MenuItem(
                            "Editing Key Bindings",
                            children=[
                                SmartMenuItem(
                                    "Emacs",
                                    handler=lambda: self.set_edit_mode("emacs"),
                                    toggler=Condition(
                                        lambda: config.key_map == "emacs"
                                    ),
                                ),
                                SmartMenuItem(
                                    "Vi",
                                    handler=lambda: self.set_edit_mode("vi"),
                                    toggler=Condition(lambda: config.key_map == "vi"),
                                ),
                            ],
                        ),
                        MenuItem(
                            "Switch Background Pattern",
                            handler=lambda: config.toggle("background_pattern"),
                        ),
                        SmartMenuItem(
                            "Run cell after external edit",
                            toggler=Condition(
                                lambda: bool(config.run_after_external_edit)
                            ),
                            handler=lambda: config.toggle("run_after_external_edit"),
                        ),
                        SmartMenuItem(
                            "Auto-complete",
                            toggler=Condition(lambda: bool(config.autocomplete)),
                            handler=lambda: config.toggle("autocomplete"),
                        ),
                        SmartMenuItem(
                            "Auto-suggest",
                            toggler=Condition(lambda: bool(config.autosuggest)),
                            handler=lambda: config.toggle("autosuggest"),
                        ),
                    ],
                ),
                MenuItem(
                    " Help ",
                    children=[
                        MenuItem("Keyboard Shortcuts", handler=self.help_keys),
                        MenuItem("Logs", handler=self.help_logs),
                        MenuItem("About", handler=self.help_about),
                    ],
                ),
            ],
        )

        self.logo = FormattedTextControl(
            [("", f" {__logo__} ")],
            focusable=True,
            show_cursor=False,
            style="class:menu-bar.item,logo",
        )

        # Add logo and status bar into menubar
        assert isinstance(self.body_container.container.content, HSplit)
        self.body_container.container.content.children = [
            VSplit(
                [
                    Window(self.logo, height=D.exact(1), dont_extend_width=True),
                    self.body_container.window,
                    self.status_bar,
                ]
            ),
            self.body_container.container.content.children[1],
        ]

        self.root_container = FloatContainer(
            content=self.body_container,
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16, scroll_offset=1),
                )
            ],
        )

        return self.root_container

    def set_edit_mode(self, mode: "str") -> "None":
        """Sets the keybindings for editing mode.

        Args:
            mode: 'vi' or 'emacs'

        """
        config.key_map = mode
        self.editing_mode = self.get_edit_mode()

    def get_edit_mode(self) -> "EditingMode":
        """Returns the editing mode enum defined in the configuration."""
        return {"emacs": EditingMode.EMACS, "vi": EditingMode.VI}.get(
            str(config.key_map), EditingMode.EMACS
        )

    def load_key_bindings(self) -> "KeyBindings":
        """Define application-wide keybindings."""
        kb = KeyBindingsInfo()

        @Condition
        def in_edit_mode() -> "bool":
            if self.tab is not None:
                cell = getattr(self.tab, "cell", False)
                if cell:
                    if cell.is_editing():
                        return True
            return False

        @kb.add("c-n", group="Application", desc="Create a new notebook file")
        def new(event: "KeyPressEvent") -> None:
            self.ask_open_file(validate=False)

        @kb.add("c-o", group="Application", desc="Open file")
        def open(event: "KeyPressEvent") -> None:
            self.ask_open_file()

        @kb.add("c-w", group="Application", desc="Close the current tab")
        def close(event: "KeyPressEvent") -> None:
            self.close_tab(self.tab)

        @kb.add("c-q", group="Application", desc="Quit euporie")
        def exit(event: "KeyPressEvent") -> None:
            self.try_to_exit()

        kb.add(
            "tab", filter=~in_edit_mode, group="Navigation", desc="Focus next element"
        )(focus_next)
        kb.add(
            "s-tab",
            filter=~in_edit_mode,
            group="Navigation",
            desc="Focus previous element",
        )(focus_previous)

        return kb

    def try_to_exit(self) -> "None":
        """Check for unsaved files before closing.

        Creates a chain of close file commands, where the callback for each triggers
        the closure of the next. The closing process can be cancelled anywhere along
        the chain.
        """
        if self.tabs:

            def final_cb() -> "None":
                """Really exit after the last tab in the chain is closed."""
                self.cleanup_closed_tab(self.tabs[0])
                self.exit()

            def create_cb(
                close_tab: "Tab", cleanup_tab: "Tab", cb: "Callable"
            ) -> "Callable":
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
            self.exit()
