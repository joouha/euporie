# -*- coding: utf-8 -*-
"""Contains the main Application class which runs euporie."""
from __future__ import annotations

import logging
import sys
from asyncio import AbstractEventLoop
from typing import Any, Callable, Optional

from prompt_toolkit.formatted_text import (
    AnyFormattedText,
    fragment_list_to_text,
    to_formatted_text,
)
from prompt_toolkit.layout import Float, HSplit, Layout, Window
from prompt_toolkit.layout.containers import AnyContainer, FloatContainer
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.widgets import Button, Dialog, Label

from euporie import __version__, _app_name, logo
from euporie.keys import KeyBindingsInfo
from euporie.log import log_memory
from euporie.text import ANSI, FormattedTextArea

log = logging.getLogger(__name__)


class AppDialogMixin:
    """Provides dialogs for the main application."""

    root_container: "FloatContainer"
    layout: "Layout"

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
                        ("class:logo", logo),
                        ("bold", f" {_app_name}"),
                        ("", f"Version {__version__}\n\n".rjust(27, " ")),
                        ("", "A TUI editor for Jupyter notebooks\n"),
                        ("class:hr", "─" * 34 + "\n\n"),
                        ("", "© 2021 Josiah Outram Halstead"),
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
