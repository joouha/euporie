# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import traceback
from functools import partial
from pathlib import Path

from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.eventloop import get_traceback_from_context
from prompt_toolkit.filters import Condition, buffer_has_focus, has_completions
from prompt_toolkit.formatted_text import (
    HTML,
    AnyFormattedText,
    fragment_list_to_text,
    to_formatted_text,
)
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
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.widgets import (
    Button,
    Dialog,
    Label,
    MenuContainer,
    MenuItem,
    TextArea,
)
from pygments.styles import get_all_styles  # type: ignore
from rich.traceback import Traceback

from euporie import __app_name__, __copyright__, __logo__, __strapline__, __version__
from euporie.app.base import BaseApp
from euporie.box import Pattern
from euporie.config import config
from euporie.keys import KeyBindingsInfo
from euporie.log import LogView
from euporie.menu import SmartMenuItem
from euporie.render import RichRenderer
from euporie.text import ANSI, FormattedTextArea

log = logging.getLogger(__name__)


class TuiApp(BaseApp):
    def __init__(self, **kwargs):
        super().__init__(
            full_screen=True,
            mouse_support=True,
            notebook_kwargs=dict(
                interactive=True,
                autorun=config.run,
                scroll=True,
            ),
            **kwargs,
        )
        # Ensure an opened tab is focused
        if self.tab:
            self.pre_run_callables.append(self.tab.focus)

    def format_title(self) -> "StyleAndTextTuples":
        if self.tab:
            return [("bold class:menu-bar.item", f" {self.tab.path.name} ")]
        else:
            return []

    def format_status(self, part: "str") -> "StyleAndTextTuples":
        if self.tab:
            entries = self.tab.statusbar_fields()
        else:
            entries = (
                [HTML("Press <b>Ctrl+n</b> to start a new notebook")],
                [HTML("Press <b>Ctrl+q</b> to quit")],
            )
        output = []
        for field in entries[0 if part == "left" else 1]:
            if field:
                if isinstance(field, tuple):
                    ft = [field]
                else:
                    ft = to_formatted_text(field, style="class:status.field")
                output += [
                    ("class:status.field", " "),
                    *ft,
                    ("class:status.field", " "),
                    ("class:status", " "),
                ]
        if output:
            output.pop()
        return output

    def load_container(self) -> "AnyContainer":
        """Builds the main application layout."""

        self.root_container = MenuContainer(
            body=HSplit(
                [
                    DynamicContainer(self.tab_container),
                    ConditionalContainer(
                        content=VSplit(
                            [
                                Window(
                                    FormattedTextControl(
                                        lambda: self.format_status(part="left")
                                    ),
                                    style="class:status",
                                ),
                                Window(
                                    FormattedTextControl(
                                        lambda: self.format_status(part="right")
                                    ),
                                    style="class:status.right",
                                    align=WindowAlign.RIGHT,
                                ),
                            ],
                            height=1,
                        ),
                        filter=Condition(lambda: not config.show_status_bar),
                    ),
                ]
            ),
            menu_items=[
                MenuItem(
                    " File ",
                    children=[
                        MenuItem("New", handler=self.ask_new_file),
                        MenuItem("Open", handler=self.ask_open_file),
                        MenuItem("-", disabled=True),
                        SmartMenuItem(
                            "Save",
                            handler=lambda: self.tab_op("save"),
                            disabler=~self.has_tab,
                        ),
                        SmartMenuItem(
                            "Close",
                            handler=self.close_tab,
                            disabler=~self.has_tab,
                        ),
                        MenuItem("-", disabled=True),
                        MenuItem("Exit", handler=self.exit),
                    ],
                ),
                MenuItem(
                    " Edit ",
                    children=[
                        SmartMenuItem(
                            "Cut Cell",
                            handler=lambda: self.tab_op("cut"),
                            disabler=~self.has_tab,
                        ),
                        SmartMenuItem(
                            "Copy Cell",
                            handler=lambda: self.tab_op("copy"),
                            disabler=~self.has_tab,
                        ),
                        SmartMenuItem(
                            "Paste Cell",
                            handler=lambda: self.tab_op("paste"),
                            disabler=~self.has_tab,
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
                            disabler=~self.has_tab,
                        ),
                        SmartMenuItem(
                            "Restart Kernel",
                            handler=lambda: self.tab_op("restart_kernel"),
                            disabler=~self.has_tab,
                        ),
                        SmartMenuItem(
                            "Change Kernel...",
                            handler=lambda: self.tab_op("change_kernel"),
                            disabler=~self.has_tab,
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
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=16, scroll_offset=1),
                )
            ],
        )

        self.logo = Window(
            FormattedTextControl(
                [("", f" {__logo__} ")],
                focusable=True,
                show_cursor=False,
                style="class:menu-bar.item,logo",
            ),
            height=1,
            dont_extend_width=True,
        )

        self.title_bar = ConditionalContainer(
            Window(
                content=FormattedTextControl(
                    self.format_title, focusable=True, show_cursor=False
                ),
                height=1,
                style="class:menu-bar",
                dont_extend_width=True,
                align=WindowAlign.RIGHT,
            ),
            filter=self.has_tab,
        )

        # Add logo and status bar into menubar
        assert isinstance(self.root_container.container.content, HSplit)
        self.root_container.container.content.children = [
            VSplit(
                [
                    self.logo,
                    self.root_container.window,
                    self.title_bar,
                ]
            ),
            self.root_container.container.content.children[1],
        ]

        return self.root_container

    def tab_container(self) -> "AnyContainer":
        """Returns a container with all opened tabs.

        Returns:
            A vertical split containing the opened tab containers.

        """
        if self.tabs:
            return VSplit(
                self.tabs,
                padding=1,
                padding_char=" ",
                padding_style="class:chrome",
            )
        else:
            return Pattern()

    def load_key_bindings(self) -> "KeyBindings":
        """Define application-wide keybindings."""
        kb = super().load_key_bindings()

        if config.debug:

            @kb.add(">")
            def test_exception(event: "KeyPressEvent") -> None:
                log.debug("Raising test exception")
                raise Exception("Test exception, please ignore")

        kb.add("c-n", group="Application", desc="Create a new notebook file")(
            self.ask_new_file
        )

        kb.add("c-o", group="Application", desc="Open file")(self.ask_open_file)

        @kb.add("c-w", group="Application", desc="Close the current tab")
        def close(event: "KeyPressEvent") -> None:
            self.close_tab(self.tab)

        kb.add(
            "tab",
            group="Navigation",
            desc="Focus next element",
            filter=~has_completions & ~buffer_has_focus,
        )(focus_next)
        kb.add(
            "s-tab",
            group="Navigation",
            desc="Focus previous element",
            filter=~has_completions & ~buffer_has_focus,
        )(focus_previous)

        return kb

    def dialog(
        self,
        title: "AnyFormattedText",
        body: "AnyContainer",
        buttons: "dict[str, Optional[Callable]]",
        to_focus: "Optional[AnyContainer]" = None,
    ) -> None:
        """Display a modal dialog above the application.

        Returns focus to the previously selected control when closed.

        Args:
            title: The title of the dialog. Can be formatted text.
            body: The container to use as the main body of the dialog.
            buttons: A dictionary mapping text to display as dialog buttons to
                callbacks to run when the button is clicked. If the callback is
                `None`, the dialog will be closed without running a callback.
            to_focus: The control to focus when the dialog is displayed.

        """
        focused = self.layout.current_control

        def _make_handler(cb: "Optional[Callable]" = None) -> "Callable":
            def inner() -> "None":
                self.root_container.floats.remove(dialog)
                if focused in self.layout.find_all_controls():
                    try:
                        self.layout.focus(focused)
                    except ValueError:
                        pass
                if callable(cb):
                    cb()

            return inner

        # kb = KeyBindingsInfo()
        # kb.add("escape")(lambda event: _make_handler())
        button_widgets = []
        for text, cb in buttons.items():
            handler = _make_handler(cb)
            button_widgets.append(
                Button(text, handler, left_symbol="[", right_symbol="]")
            )
            # kb.add(text[:1].lower())(lambda event: handler)

        dialog = Float(
            Dialog(
                title=title,
                body=body,
                buttons=button_widgets,
                modal=True,
                with_background=True,
            )
        )

        try:
            self.root_container.floats.insert(0, dialog)
        except:
            log.exception("")

        if to_focus is None:
            to_focus = button_widgets[0]
        self.layout.focus(to_focus)

    def ask_new_file(self, event=None):
        return self.ask_file(
            validate=False,
            completer=PathCompleter(),
        )

    def ask_open_file(self, event=None):
        return self.ask_file(
            completer=PathCompleter(),
        )

    def ask_file(
        self,
        default: "str" = "",
        validate: "bool" = True,
        error: "Optional[str]" = None,
        completer: "Completer" = None,
    ) -> None:
        """Display a dialog asking for file name input.

        Args:
            default: The default filename to display in the text entry box
            validate: Whether to disallow files which do not exist
            error: An optional error message to display below the file name

        """

        def _open_cb() -> None:
            if not validate or Path(filepath.text).expanduser().exists():
                self.open_file(filepath.text)
            else:
                try:
                    self.ask_open_file(
                        default=filepath.text,
                        validate=validate,
                        error="File not found",
                        completer=completer,
                    )
                except Exception:
                    log.exception()

        def _accept_text(buf):
            self.layout.focus_next()
            buf.complete_state = None
            return True

        filepath = TextArea(
            text=default,
            multiline=False,
            completer=completer,
            accept_handler=_accept_text,
        )

        root_contents: "list[AnyContainer]" = [
            Label("Enter file name:"),
            filepath,
        ]
        if error:
            root_contents.append(Label(error, style="red"))
        self.dialog(
            title="Select file",
            body=HSplit(root_contents),
            buttons={
                "OK": _open_cb,
                "Cancel": None,
            },
            to_focus=filepath,
        )

    def help_keys(self) -> None:
        """Displays details of registered key-bindings in a dialog."""
        key_details = KeyBindingsInfo.to_formatted_text()
        max_line_width = max(
            [len(line) for line in fragment_list_to_text(key_details).split("\n")]
        )
        body = FormattedTextArea(
            formatted_text=key_details,
            multiline=True,
            focusable=True,
            wrap_lines=False,
            width=Dimension(preferred=max_line_width + 2),
            scrollbar=True,
        )

        self.dialog(
            title="Keyboard Shortcuts",
            body=body,
            buttons={"OK": None},
        )

    def help_logs(self) -> None:
        """Displays a dialog with logs."""
        for tab in self.tabs:
            if isinstance(tab, LogView):
                break
        else:
            tab = LogView()
            self.tabs.append(tab)
        self.layout.focus(tab)

    def help_about(self) -> None:
        """Displays an about dialog."""
        self.dialog(
            title="About",
            body=Window(
                FormattedTextControl(
                    [
                        ("class:logo", __logo__),
                        ("", " "),
                        ("bold", __app_name__),
                        ("", f"Version {__version__}\n\n".rjust(27, " ")),
                        ("", __strapline__),
                        ("", "\n"),
                        ("class:hr", "─" * 34 + "\n\n"),
                        ("", __copyright__),
                    ]
                ),
                dont_extend_height=True,
            ),
            buttons={"OK": None},
        )

    def _handle_exception(
        self, loop: "AbstractEventLoop", context: "dict[str, Any]"
    ) -> None:
        exception = context.get("exception")
        # Log observed exceptions to the log
        log.exception("An unhandled exception occured", exc_info=exception)
        # Also display a dialog to the user
        self.dialog(
            title="Error",
            body=Window(
                FormattedTextControl(
                    [
                        ("bold", "An error occured:\n\n"),
                        ("", exception.__repr__()),
                    ]
                )
            ),
            buttons={"OK": None},
        )

    def exit(self) -> "None":
        """Check for unsaved files before closing.

        Creates a chain of close file commands, where the callback for each triggers
        the closure of the next. The closing process can be cancelled anywhere along
        the chain.
        """
        really_close = super().exit
        if self.tabs:

            def final_cb() -> "None":
                """Really exit after the last tab in the chain is closed."""
                self.cleanup_closed_tab(self.tabs[0])
                really_close()

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
            really_close()
