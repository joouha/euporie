# -*- coding: utf-8 -*-
"""Contains the main Application class which runs euporie."""
from __future__ import annotations

import logging
import sys
from asyncio import AbstractEventLoop
from pathlib import Path
from typing import Any, Callable, Optional

from prompt_toolkit.formatted_text import (
    AnyFormattedText,
    fragment_list_to_text,
    to_formatted_text,
)
from prompt_toolkit.layout import Float, HSplit, Layout, Window
from prompt_toolkit.layout.containers import AnyContainer, FloatContainer, to_container
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.widgets import Button, Dialog, Label, TextArea

from euporie import __app_name__, __copyright__, __logo__, __strapline__, __version__
from euporie.keys import KeyBindingsInfo
from euporie.log import log_memory
from euporie.text import ANSI, FormattedTextArea

log = logging.getLogger(__name__)


class DialogMixin:
    """Provides dialogs for the main application."""

    root_container: "FloatContainer"
    layout: "Layout"
    open_file: "Callable"

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

        def _make_handler(cb: "Optional[Callable]") -> "Callable":
            def inner() -> "None":
                self.root_container.floats.remove(dialog)
                self.layout.focus(focused)
                if cb:
                    cb()

            return inner

        focused = self.layout.current_control

        button_widgets = [
            Button(text, _make_handler(cb), left_symbol="[", right_symbol="]")
            for text, cb in buttons.items()
        ]

        dialog = Float(
            Dialog(
                title=title,
                body=body,
                buttons=button_widgets,
                modal=True,
                with_background=True,
            )
        )
        self.root_container.floats.append(
            dialog,
        )
        if to_focus is None:
            to_focus = button_widgets[0]
        self.layout.focus(to_focus)

    def ask_open_file(
        self,
        default: "str" = "",
        validate: "bool" = True,
        error: "Optional[str]" = None,
    ) -> None:
        """Display a dialog asking for file name input.

        Args:
            default: The default filename to display in the text entry box
            validate: Whether to disallow files which do not exist
            error: An optional error message to display below the file name

        """
        filepath = TextArea(text=default, multiline=False)

        def _open_cb() -> None:
            path = filepath.text
            if not validate or Path(path).expanduser().exists():
                self.open_file(filepath.text)
            else:
                self.ask_open_file(
                    default=filepath.text, validate=validate, error="File not found"
                )

        body_contents: "list[AnyContainer]" = [
            Label("Enter file name:"),
            filepath,
        ]
        if error:
            body_contents.append(to_container(Label(error, style="red")))
        self.dialog(
            title="Select file",
            body=HSplit(body_contents),
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
            width=D(preferred=max_line_width + 2),
            scrollbar=True,
        )

        self.dialog(
            title="Keyboard Shortcuts",
            body=body,
            buttons={"OK": None},
        )

    def help_logs(self) -> None:
        """Displays a dialog with logs."""
        log_memory.seek(0)
        log_data = to_formatted_text(ANSI(log_memory.read()))

        body = FormattedTextArea(
            formatted_text=log_data,
            multiline=True,
            focusable=True,
            wrap_lines=False,
            width=D(preferred=120),
            scrollbar=True,
        )
        self.dialog(
            title="Logs",
            body=body,
            buttons={"OK": None},
        )

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
        from prompt_toolkit.formatted_text import to_formatted_text
        from rich.traceback import Traceback

        from euporie.render import RichRenderer

        # Log observed exceptions to the log
        log.error("An unhandled exception occured", exc_info=sys.exc_info())

        # Also display a dialog to the user
        formatted_tb = to_formatted_text(
            ANSI(RichRenderer().render(Traceback(), width=80, height=999))
        )
        tb_control = FormattedTextArea(
            formatted_text=formatted_tb,
            multiline=True,
            focusable=True,
            wrap_lines=False,
            width=D(preferred=81),
            height=D(max=15),
            scrollbar=True,
        )
        self.dialog(
            title="Error",
            body=HSplit(
                [
                    Label("An error occured:\n", style="bold"),
                    tb_control,
                ]
            ),
            buttons={"OK": None},
        )
