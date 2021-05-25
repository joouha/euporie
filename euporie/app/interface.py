# -*- coding: utf-8 -*-
"""Contains the main Application class which runs euporie."""
from __future__ import annotations

import logging
from functools import partial
from typing import TYPE_CHECKING, Callable

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

from euporie import __logo__
from euporie.app.dialog import DialogMixin
from euporie.config import config
from euporie.keys import KeyBindingsInfo
from euporie.menu import SmartMenuItem
from euporie.notebook import File, Notebook
from euporie.scroll import ScrollingContainer

if TYPE_CHECKING:
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.key_binding.key_processor import KeyPressEvent
    from prompt_toolkit.layout.containers import AnyContainer

log = logging.getLogger(__name__)


class InterfaceMixin(DialogMixin):
    """Provides user interface."""

    pre_run: "list[Callable]"
    file_op: "Callable"
    files: "list[File]"
    file: "AnyContainer"
    is_file_open: "Condition"
    close_file: "Callable"
    update_style: "Callable"
    cleanup_closed_file: "Callable"
    exit: "Callable"
    # output: "Optional[Output]"

    def setup(self) -> "None":
        """Create an output and set pre-run commands."""
        # Create an output
        self.output = create_output()
        # Ensure a file is focused if one has been opened
        self.pre_run.append(lambda: self.file_op("focus"))

    def file_container(self) -> "AnyContainer":
        """Returns a container with all opened files.

        A 1 column window is added to the left as padding.

        Returns:
            A vertical split containing the opened file containers.

        """
        return VSplit([Window(width=1), *self.files])

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
            file = self.file
            assert isinstance(file, Notebook)
            kernel_status = kernel_status_repr.get(file.kernel_status, "◌")
            assert isinstance(file.page, ScrollingContainer)
            selected_cell = file.page.selected_index + 1
            dirt = "*" if file.dirty else ""
            return [
                ("class:menu-bar.item", f" Cell {selected_cell} "),
                ("", " "),
                ("class:menu-bar.item bold", f" {dirt}{file.path.name} "),
                ("", " "),
                ("class:menu-bar.item", f" {file.kernel_name} {kernel_status} "),
            ]

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
            filter=self.is_file_open,
        )

        self.body_container = MenuContainer(
            body=DynamicContainer(self.file_container),
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
                            handler=lambda: self.file_op("save"),
                            disabler=~self.is_file_open,
                        ),
                        SmartMenuItem(
                            "Close",
                            handler=self.close_file,
                            disabler=~self.is_file_open,
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
                            handler=lambda: self.file_op("cut"),
                            disabler=~self.is_file_open,
                        ),
                        SmartMenuItem(
                            "Copy Cell",
                            handler=lambda: self.file_op("copy"),
                            disabler=~self.is_file_open,
                        ),
                        SmartMenuItem(
                            "Paste Cell",
                            handler=lambda: self.file_op("paste"),
                            disabler=~self.is_file_open,
                        ),
                    ],
                ),
                MenuItem(
                    " Kernel ",
                    children=[
                        MenuItem(
                            "Restart Kernel",
                            handler=lambda: self.file_op("restart_kernel"),
                        ),
                        MenuItem(
                            "Change Kernel...",
                            handler=lambda: self.file_op("change_kernel"),
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
                                            lambda x: config.pygments_style == x, style
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
                                        lambda: config.editing_mode == "emacs"
                                    ),
                                ),
                                SmartMenuItem(
                                    "Vi",
                                    handler=lambda: self.set_edit_mode("vi"),
                                    toggler=Condition(
                                        lambda: config.editing_mode == "vi"
                                    ),
                                ),
                            ],
                        ),
                        MenuItem(
                            "Switch Background Pattern",
                            handler=lambda: config.toggle("background"),
                        ),
                        SmartMenuItem(
                            "Run cell after external edit",
                            toggler=Condition(
                                lambda: bool(config.execute_after_external_edit)
                            ),
                            handler=lambda: config.toggle(
                                "execute_after_external_edit"
                            ),
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
        config.editing_mode = mode
        self.editing_mode = self.get_edit_mode()

    def get_edit_mode(self) -> "EditingMode":
        """Returns the editing mode enum defined in the configuration."""
        return {"emacs": EditingMode.EMACS, "vi": EditingMode.VI}.get(
            str(config.editing_mode), EditingMode.EMACS
        )

    def load_key_bindings(self) -> "KeyBindings":
        """Define application-wide keybindings."""
        kb = KeyBindingsInfo()

        @Condition
        def in_edit_mode() -> "bool":
            assert isinstance(self.file, File)
            file = self.file
            if file:
                cell = getattr(self.file, "cell", False)
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

        @kb.add("c-w", group="Application", desc="Close the current file")
        def close(event: "KeyPressEvent") -> None:
            self.close_file(self.file)

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
        if self.files:

            def final_cb() -> "None":
                """Really exit after the last file in the chain is closed."""
                self.cleanup_closed_file(self.files[0])
                self.exit()

            def create_cb(
                close_file: "File", cleanup_file: "File", cb: "Callable"
            ) -> "Callable":
                """Generate a file close chaining callbacks.

                Cleans up after the previously closed file, and requests to close the
                next file in the chain.

                Args:
                    close_file: The file to close
                    cleanup_file: The previously closed file to cleanup
                    cb: The callback to call when work is complete

                Returns:
                    A callback function which cleans up `cleanup_file` and closes
                        `close_file`.

                """

                def inner() -> None:
                    self.cleanup_closed_file(cleanup_file)
                    close_file.close(cb=cb)

                return inner

            cb = final_cb
            for close_file, cleanup_file in zip(self.files, self.files[1:]):
                cb = create_cb(close_file, cleanup_file, cb)
            self.files[-1].close(cb)
        else:
            self.exit()
