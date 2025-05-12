"""Concern dumping output."""

from __future__ import annotations

import io
import logging
import os
import sys
from functools import partial
from typing import TYPE_CHECKING, cast

from prompt_toolkit.layout.containers import DynamicContainer, FloatContainer, Window
from prompt_toolkit.output.defaults import create_output
from prompt_toolkit.output.vt100 import Vt100_Output

from euporie.core.app.app import BaseApp
from euporie.core.app.current import get_app
from euporie.core.io import PseudoTTY
from euporie.core.key_binding.registry import register_bindings
from euporie.preview.tabs.notebook import PreviewNotebook

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, TextIO

    from prompt_toolkit.application.application import _AppResult
    from prompt_toolkit.layout.containers import Float
    from prompt_toolkit.output import Output

    from euporie.core.tabs.base import Tab

log = logging.getLogger(__name__)


class PreviewApp(BaseApp):
    """Preview app.

    Preview notebook files in the terminal.

    Outputs a formatted notebook file. The formatted output will be written to
    the the output file path given by `output_file` (the standard output by
    default).

    """

    name = "preview"

    def __init__(self, **kwargs: Any) -> None:
        """Create an app for dumping a prompt-toolkit layout."""
        # Set default arguments
        kwargs.setdefault("title", "euporie-preview")
        kwargs.setdefault("leave_graphics", True)
        kwargs.setdefault("full_screen", False)
        kwargs.setdefault("max_render_postpone_time", 0)
        kwargs.setdefault("min_redraw_interval", 0)
        kwargs.setdefault("extend_renderer_height", True)
        kwargs.setdefault("enable_page_navigation_bindings", False)
        # Adjust options if we are paging output
        if self.config.page:
            kwargs.setdefault("set_title", False)
            kwargs.setdefault("extend_renderer_width", True)
        # Initialise the application
        super().__init__(**kwargs)
        # We want the app to close when rendering is complete
        # self.after_render += self.pre_exit
        # Do not load any key bindings
        self.bindings_to_load.append("euporie.preview.app:PreviewApp")
        # Select the first tab after files are opened
        self.pre_run_callables.append(partial(setattr, self, "tab_idx", 0))

    def get_file_tab(self, path: Path) -> type[Tab]:
        """Return the tab to use for a file path."""
        return PreviewNotebook

    def exit(
        self,
        result: _AppResult | None = None,
        exception: BaseException | type[BaseException] | None = None,
        style: str = "",
    ) -> None:
        """Optionally pipe the output to a pager on exit."""
        # Display pager if needed
        if self.config.page:
            from pydoc import pager

            output_file = getattr(self.output, "output_file")  # noqa: B009
            if output_file is not None:
                output_file.seek(0)
                data = output_file.read()
                pager(data)
        if exception is not None:
            super().exit(exception=exception, style=style)
        elif result is not None:
            super().exit(result=result, style=style)
        else:
            super().exit()

    def load_container(self) -> FloatContainer:
        """Return a container with all opened tabs."""
        return FloatContainer(
            DynamicContainer(lambda: self.tab or Window()),
            floats=cast("list[Float]", self.floats),
        )

    def cleanup_closed_tab(self, tab: Tab) -> None:
        """Exit if all tabs are closed."""
        super().cleanup_closed_tab(tab)
        if not self.tabs:
            self._is_running = False
            self.exit()
        self.draw(render_as_done=True)

    @classmethod
    def load_output(cls) -> Output:
        """Load the output.

        Depending on the application configuration, will set the output to a file, to
        stdout, or to a temporary file so the output can be displayed in a pager.

        Returns:
            A container for notebook output

        """
        output_file: TextIO
        if cls.config.page:
            # Use a temporary file as display output if we are going to page the output
            from tempfile import TemporaryFile

            output_file = TemporaryFile("w+")  # noqa: SIM115
            # Make this file look like a tty so we get colorful output
            output_file = cast("TextIO", PseudoTTY(output_file, isatty=True))

        else:
            # If we are not paging output, determine where to print it
            if cls.config.output_file is None or str(cls.config.output_file) in (
                "-",
                "/dev/stdout",
            ):
                output_file = sys.stdout
            elif str(cls.config.output_file) == "/dev/stderr":
                output_file = sys.stderr
            else:
                try:
                    output_file = cls.config.output_file.open("w+")
                except (
                    FileNotFoundError,
                    PermissionError,
                    io.UnsupportedOperation,
                ) as error:
                    log.error(error)
                    log.error(
                        "Output file `%s` cannot be opened. "
                        "Standard output will be used.",
                        cls.config.output_file,
                    )
                    output_file = sys.stdout

            # Make the output look like a TTY if color-depth has been configured
            if not output_file.isatty() and cls.config.color_depth is not None:
                output_file = cast(
                    "TextIO",
                    PseudoTTY(
                        output_file,
                        isatty=True,
                    ),
                )

        # Ensure we do not receive the "Output is not a terminal" message
        Vt100_Output._fds_not_a_terminal.add(output_file.fileno())
        # Set environment variable to disable character position requests
        os.environ["PROMPT_TOOLKIT_NO_CPR"] = "1"
        # Create a default output - this detects the terminal type
        # Do not use stderr instead of stdout if stdout is not a tty
        output = create_output(cast("TextIO", output_file), always_prefer_tty=False)

        # Use the width and height of stderr (this gives us the terminal size even if
        # output is being piped to a non-tty)
        setattr(  # noqa B010
            output, "get_size", create_output(stdout=sys.stderr).get_size
        )
        # Attach the output file to the output in case we need to page it
        setattr(output, "output_file", output_file)  # noqa B010

        return output

    def _redraw(self, render_as_done: bool = False) -> None:
        """Ensure the output is always rendered as done."""
        # import time
        # time.sleep(0.1)
        super()._redraw(render_as_done=True)

    def _update_invalidate_events(self) -> None:
        """Do nothing, as we don't need invalidation events for the preview app."""

    # def load_key_bindings(self) -> None:
    #     """Do no load any additional key-bindings for the preview app."""

    # ################################# Key Bindings ##################################

    register_bindings(
        {
            "euporie.preview.app:PreviewApp": {
                "quit": ["c-c", "c-q"],
            }
        }
    )


def get_preview_app() -> PreviewApp:
    """Get the current application."""
    return cast("PreviewApp", get_app())
